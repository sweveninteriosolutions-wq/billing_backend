from datetime import datetime, timezone
from decimal import Decimal
import logging
import os
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, select
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.models.quotation_models import Quotation, QuotationItem
from app.models.customer_models import Customer
from app.models.product_models import Product
from app.schemas.quotation_schema import (
    QuotationResponse,
    QuotationOut,
    QuotationListResponse,
    QuotationCreate,
    QuotationUpdate,
    QuotationItemOut
)
from app.utils.activity_helpers import log_user_activity

logger = logging.getLogger(__name__)

GST_RATE = Decimal("0.18")  # GST rate


# --------------------------
# CREATE QUOTATION
# --------------------------
async def create_quotation(db: AsyncSession, data: QuotationCreate, current_user) -> QuotationResponse:
    try:
        # Validate customer
        customer = await db.get(Customer, data.customer_id)
        if not customer or not customer.is_active:
            raise HTTPException(status_code=404, detail=f"Customer {data.customer_id} not found or inactive")

        # Create quotation with temp number
        quotation = Quotation(
            quotation_number="TEMP",
            customer_id=data.customer_id,
            approved=False,
            moved_to_sales=False,
            moved_to_invoice=False,
            created_by=current_user.id,
            description=data.description,
            notes=data.notes,
            additional_data=data.additional_data,
            issue_date=datetime.now(timezone.utc)
        )
        db.add(quotation)
        await db.flush()

        # Generate final quotation number
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        quotation.quotation_number = f"VSF-Q-{today_str}-{quotation.id:04d}"

        # Create quotation items
        total_items_amount = Decimal("0.00")
        quotation_items = []

        for item_data in data.items:
            product = await db.get(Product, item_data.product_id)
            if not product or product.is_deleted:
                raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")

            unit_price = Decimal(str(product.price))
            total_price = unit_price * item_data.quantity
            total_items_amount += total_price

            quotation_items.append(
                QuotationItem(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=item_data.quantity,
                    total=total_price,
                    created_by=current_user.id
                )
            )

        quotation.total_items_amount = total_items_amount
        quotation.gst_amount = total_items_amount * GST_RATE
        quotation.total_amount = total_items_amount + quotation.gst_amount

        db.add_all(quotation_items)

        # Log activity
        await log_user_activity(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            message=(
                f"Created Quotation '{quotation.quotation_number}' for Customer '{customer.name}' "
                f"with {len(data.items)} items. Items Total: ₹{quotation.total_items_amount:.2f}, "
                f"GST: ₹{quotation.gst_amount:.2f}, Total Amount: ₹{quotation.total_amount:.2f}."
            )
        )

        await db.commit()

        # Refetch quotation with items
        result = await db.execute(
            select(Quotation)
            .where(Quotation.id == quotation.id)
            .options(selectinload(Quotation.items))
        )
        quotation_db = result.scalar_one()

        return QuotationResponse(
            message="Quotation created successfully",
            data=QuotationOut.model_validate(quotation_db),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating quotation: {str(e)}")


# --------------------------
# UPDATE QUOTATION
# --------------------------
async def update_quotation(db: AsyncSession, quotation_id: int, data: QuotationUpdate, current_user) -> QuotationResponse:
    quotation = (
        await db.execute(
            select(Quotation)
            .options(selectinload(Quotation.items.and_(QuotationItem.is_deleted == False)))
            .where(Quotation.id == quotation_id, Quotation.is_deleted == False)
        )
    ).unique().scalar_one_or_none()

    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales or quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Quotation cannot be edited as it is locked")

    # Update basic fields
    if data.customer_id:
        customer = await db.get(Customer, data.customer_id)
        if not customer or not customer.is_active:
            raise HTTPException(status_code=404, detail=f"Customer {data.customer_id} not found or inactive")
        quotation.customer_id = data.customer_id

    if data.notes is not None:
        quotation.notes = data.notes
    if data.description is not None:
        quotation.description = data.description

    # Update items
    if data.items:
        existing_items = {item.id: item for item in quotation.items if not item.is_deleted}
        for item_data in data.items:
            if item_data.id:
                item = existing_items.get(item_data.id)
                if not item:
                    raise HTTPException(status_code=404, detail=f"Quotation item with ID {item_data.id} not found")
                if item_data.is_deleted:
                    item.is_deleted = True
                    item.updated_by = current_user.id
                else:
                    if item_data.quantity and item_data.quantity > 0:
                        item.quantity = item_data.quantity
                        item.total = round(item.quantity * item.unit_price, 2)
                        item.updated_by = current_user.id
            else:
                product = await db.get(Product, item_data.product_id)
                if not product or product.is_deleted:
                    raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")
                if any(i.product_id == product.id and not i.is_deleted for i in quotation.items):
                    raise HTTPException(status_code=400, detail=f"Product '{product.name}' already exists in quotation")
                if item_data.quantity <= 0:
                    raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

                new_item = QuotationItem(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=item_data.quantity,
                    unit_price=product.price,
                    total=round(item_data.quantity * product.price, 2),
                    created_by=current_user.id
                )
                quotation.items.append(new_item)

    quotation.calculate_totals()
    quotation.updated_by = current_user.id
    db.add(quotation)

    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=(
            f"Updated Quotation '{quotation.quotation_number}' by '{current_user.username}'. "
            f"Customer: '{quotation.customer.name}', Items Count: {len([i for i in quotation.items if not i.is_deleted])}, "
            f"Total Amount (with GST): ₹{quotation.total_amount:.2f}."
        )
    )

    await db.commit()
    await db.refresh(quotation)
    quotation.items = [i for i in quotation.items if not i.is_deleted]

    return QuotationResponse(
        message="Quotation updated successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# DELETE QUOTATION
# --------------------------
async def delete_quotation(db: AsyncSession, quotation_id: int, _user) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales:
        raise HTTPException(status_code=400, detail="Cannot delete quotation moved to sales order")

    quotation.is_deleted = True
    quotation.updated_by = _user.id

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=(
            f"Soft-deleted Quotation '{quotation.quotation_number}' by '{_user.username}'. "
            f"Customer: '{quotation.customer.name}', Total Amount: ₹{quotation.total_amount:.2f}."
        )
    )

    await db.commit()
    return QuotationResponse(message="Quotation deleted successfully", data=None)


# --------------------------
# APPROVE QUOTATION
# --------------------------
async def approve_quotation(db: AsyncSession, quotation_id: int, _user) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation already approved")

    quotation.approved = True
    quotation.updated_by = _user.id

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=(
            f"Approved Quotation '{quotation.quotation_number}' for Customer '{quotation.customer_id}'. "
            f"Total Amount: ₹{quotation.total_amount:.2f}."
        )
    )

    await db.commit()
    await db.refresh(quotation)
    return QuotationResponse(message="Quotation approved successfully", data=QuotationOut.from_orm(quotation))


# --------------------------
# MOVE TO SALES
# --------------------------
async def move_to_sales(db: AsyncSession, quotation_id: int, _user) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales or quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Quotation already moved")
    if not quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation must be approved before moving to sales")

    quotation.moved_to_sales = True
    quotation.updated_by = _user.id

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=(
            f"Moved Quotation '{quotation.quotation_number}' to Sales Order stage for Customer '{quotation.customer_id}'. "
            f"Total Amount: ₹{quotation.total_amount:.2f}."
        )
    )

    await db.commit()
    await db.refresh(quotation)
    return QuotationResponse(message="Quotation moved to sales successfully", data=QuotationOut.from_orm(quotation))


# --------------------------
# MOVE TO INVOICE
# --------------------------
async def move_to_invoice(db: AsyncSession, quotation_id: int, _user) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales or quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Quotation already moved")
    if not quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation must be approved before moving to invoice")

    quotation.moved_to_invoice = True
    quotation.updated_by = _user.id

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=(
            f"Moved Quotation '{quotation.quotation_number}' to Invoice stage for Customer '{quotation.customer.name}'. "
            f"Total Amount: ₹{quotation.total_amount:.2f}."
        )
    )

    await db.commit()
    await db.refresh(quotation)
    return QuotationResponse(message="Quotation moved to invoice successfully", data=QuotationOut.from_orm(quotation))


# --------------------------
# DELETE QUOTATION ITEM
# --------------------------
async def delete_quotation_item(db: AsyncSession, item_id: int, _user) -> QuotationResponse:
    item = await db.get(QuotationItem, item_id)
    if not item or item.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation item not found")
    if item.quotation.moved_to_sales or item.quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Cannot delete item from locked quotation")

    item.is_deleted = True
    item.updated_by = _user.id

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=(
            f"Deleted item '{item.product_name}' (Qty: {item.quantity}, Total: ₹{item.total:.2f}) "
            f"from Quotation '{item.quotation.quotation_number}' for Customer '{item.quotation.customer.name}'."
        )
    )

    await db.commit()
    await db.refresh(item.quotation)
    return QuotationResponse(message="Quotation item deleted successfully", data=QuotationOut.from_orm(item.quotation))


# --------------------------
# GET SINGLE QUOTATION BY ID
# --------------------------
async def get_quotation(db: AsyncSession, quotation_id: int) -> QuotationResponse:
    result = await db.execute(
        select(Quotation)
        .options(selectinload(Quotation.items))
        .where(Quotation.id == quotation_id, Quotation.is_deleted == False)
    )
    quotation = result.scalars().first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    quotation.items = [item for item in quotation.items if not item.is_deleted]
    return QuotationResponse(message="Quotation retrieved successfully", data=QuotationOut.model_validate(quotation))


# --------------------------
# LIST ALL QUOTATIONS
# --------------------------
from sqlalchemy import select, and_

async def get_all_quotations_service(
    db: AsyncSession,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 10
):
    offset = (page - 1) * page_size
    conditions = [Quotation.is_deleted == False]

    if status:
        conditions.append(Quotation.status == status)
    if start_date and end_date:
        conditions.append(Quotation.created_at.between(start_date, end_date))

    query = (
        select(Quotation)
        .where(and_(*conditions))
        .order_by(Quotation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    quotations = result.unique().scalars().all()

    return [QuotationOut.from_orm(q) for q in quotations]


# --------------------------
# GET QUOTATIONS BY CUSTOMER ID
# --------------------------
async def get_quotation_list_by_CID(db: AsyncSession, customer_id: int) -> QuotationListResponse:
    result = await db.execute(
        select(Quotation)
        .options(selectinload(Quotation.items))
        .where(Quotation.customer_id == customer_id, Quotation.is_deleted == False)
    )
    quotations = result.scalars().all()
    if not quotations:
        raise HTTPException(status_code=404, detail="Quotations not found")

    quotations_out = []
    for q in quotations:
        active_items = [item for item in q.items if not item.is_deleted]
        q_out = QuotationOut.from_orm(q)
        q_out.items = [QuotationItemOut.from_orm(item) for item in active_items]
        quotations_out.append(q_out)

    return QuotationListResponse(message="Quotations retrieved successfully", data=quotations_out)


async def generate_quotation_pdf(db: AsyncSession, quotation_id: int):
    """
    Generate a professional quotation PDF with customer info,
    items, GST, and total breakdown.
    """

    # -------------------------------
    # 1️⃣ Fetch quotation with related data
    # -------------------------------
    result = await db.execute(
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_deleted == False)
    )
    quotation = result.scalars().first()

    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    # Fetch customer
    customer_result = await db.execute(
        select(Customer).where(Customer.id == quotation.customer_id)
    )
    customer = customer_result.scalars().first()

    # Fetch items
    item_result = await db.execute(
        select(QuotationItem)
        .where(QuotationItem.quotation_id == quotation.id, QuotationItem.is_deleted == False)
    )
    items = item_result.scalars().all()

    # -------------------------------
    # 2️⃣ Prepare file
    # -------------------------------
    os.makedirs("generated_pdfs", exist_ok=True)
    file_name = f"quotation_{quotation.quotation_number or quotation.id}.pdf"
    file_path = os.path.join("generated_pdfs", file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    styles = getSampleStyleSheet()
    elements = []

    # -------------------------------
    # 3️⃣ Header
    # -------------------------------
    elements.append(Paragraph("<b>Sweven Interio Solutions</b>", styles["Title"]))
    elements.append(Paragraph("Billing & Interior Design Solutions", styles["Normal"]))
    elements.append(Paragraph("Email: support@sweveninterio.com | Phone: +91 98765 43210", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>Quotation #: </b>{quotation.quotation_number}", styles["Heading2"]))
    elements.append(Paragraph(f"Issue Date: {quotation.issue_date.strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    # -------------------------------
    # 4️⃣ Customer Info
    # -------------------------------
    if customer:
        elements.append(Paragraph("<b>Customer Details</b>", styles["Heading3"]))
        elements.append(Paragraph(f"Name: {customer.name}", styles["Normal"]))
        elements.append(Paragraph(f"Email: {customer.email}", styles["Normal"]))
        elements.append(Paragraph(f"Phone: {customer.phone or '-'}", styles["Normal"]))

        # Address might be JSON
        address = customer.address
        if isinstance(address, dict):
            addr_str = ", ".join(v for v in address.values() if v)
        else:
            addr_str = str(address) if address else "-"
        elements.append(Paragraph(f"Address: {addr_str}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    # -------------------------------
    # 5️⃣ Table Header
    # -------------------------------
    data = [["#", "Product", "Qty", "Unit Price", "Total (Excl. GST)"]]
    subtotal = 0

    for i, item in enumerate(items, start=1):
        # Try to fetch product for better name if available
        product_name = item.product_name
        product_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = product_result.scalars().first()
        if product and not product.is_deleted:
            product_name = product.name

        total = float(item.total or 0)
        subtotal += total

        data.append([
            i,
            product_name,
            item.quantity,
            f"₹{float(item.unit_price):.2f}",
            f"₹{total:.2f}",
        ])

    # -------------------------------
    # 6️⃣ Totals Section
    # -------------------------------
    gst_amt = float(quotation.gst_amount or 0)
    grand_total = float(quotation.total_amount or subtotal + gst_amt)

    data.append(["", "", "", "Subtotal", f"₹{subtotal:.2f}"])
    data.append(["", "", "", "GST (18%)", f"₹{gst_amt:.2f}"])
    data.append(["", "", "", "<b>Grand Total</b>", f"<b>₹{grand_total:.2f}</b>"])

    table = Table(data, colWidths=[25, 200, 60, 80, 80])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 20))

    # -------------------------------
    # 7️⃣ Notes
    # -------------------------------
    if quotation.notes:
        elements.append(Paragraph("<b>Notes:</b>", styles["Heading3"]))
        elements.append(Paragraph(quotation.notes, styles["Normal"]))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Thank you for choosing Sweven Interio Solutions!", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # -------------------------------
    # ✅ Build PDF
    # -------------------------------
    doc.build(elements)
    return file_path

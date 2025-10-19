# app/services/billing_services/quotation_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from datetime import datetime
from typing import List, Dict, Any, Optional
from typing import List, Dict, Any, Optional

from app.models.billing_models.quotation_models import Quotation, QuotationItem
from app.models.billing_models.customer_models import Customer
from app.models.inventory_models import Product
from app.schemas.billing_schemas.quotation_schema import (
    QuotationResponse,
    QuotationOut,
    QuotationListResponse,
    QuotationCreate,
    QuotationUpdate,
    QuotationItemOut
)
from app.utils.activity_helpers import log_user_activity
import logging

logger = logging.getLogger(__name__)


# --------------------------
# Helper: Generate unique quotation number
# --------------------------
async def generate_quotation_number(db: AsyncSession) -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    result = await db.execute(select(func.max(Quotation.id)))
    last_id = result.scalar() or 0
    sequence_number = last_id + 1
    return f"VSF-Q-{today_str}-{sequence_number:04d}"


# --------------------------
# CREATE QUOTATION
# --------------------------
async def create_quotation(db: AsyncSession, data: QuotationCreate, current_user) -> QuotationResponse:
    customer_id = data.customer_id
    items = data.items  # list of QuotationItemCreate

    customer = await db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found or is inactive")

    quotation_number = await generate_quotation_number(db)

    quotation = Quotation(
        customer_id=customer_id,
        quotation_number=quotation_number,
        approved=False,
        moved_to_sales=False,
        moved_to_invoice=False,
        created_by=current_user.id
    )

    if data.notes:
        quotation.notes = data.notes
    if data.description:
        quotation.description = data.description
    if data.additional_data:
        quotation.additional_data = data.additional_data

    # Add items
    for item_data in items:
        product = await db.get(Product, item_data.product_id)
        if not product or product.is_deleted:
            raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")

        if any(item.product_id == product.id for item in quotation.items):
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.name}' is already added to this quotation"
            )

        total = round(item_data.quantity * product.price, 2)
        quotation.items.append(QuotationItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item_data.quantity,
            total=total,
            created_by=current_user.id
        ))

    db.add(quotation)
    await db.flush()

    # Audit log
    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Quotation '{quotation_number}' created by user '{current_user.username}'"
    )

    await db.commit()
    await db.refresh(quotation)

    return QuotationResponse(
        message="Quotation created successfully",
        data=QuotationOut.from_orm(quotation)
    )


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

    return QuotationResponse(
        message="Quotation retrieved successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# LIST ALL QUOTATIONS
# --------------------------
async def list_quotations(db: AsyncSession) -> QuotationListResponse:
    result = await db.execute(
        select(Quotation)
        .options(selectinload(Quotation.items))
        .where(Quotation.is_deleted == False)
    )
    quotations = result.scalars().all()

    quotations_out = []
    for q in quotations:
        active_items = [item for item in q.items if not item.is_deleted]
        q_out = QuotationOut.from_orm(q)
        q_out.items = [QuotationItemOut.from_orm(item) for item in active_items]
        quotations_out.append(q_out)

    return QuotationListResponse(
        message="Quotations retrieved successfully",
        data=quotations_out
    )


# --------------------------
# GET QUOTATIONS BY CUSTOMER
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

    return QuotationListResponse(
        message="Quotations retrieved successfully",
        data=quotations_out
    )


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
    if quotation.moved_to_sales:
        raise HTTPException(status_code=400, detail="Quotation already moved to sales order; cannot edit")
    if quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Quotation already moved to invoice; cannot edit")

    # Update customer
    if data.customer_id is not None:
        customer = await db.get(Customer, data.customer_id)
        if not customer or not customer.is_active:
            raise HTTPException(status_code=404, detail=f"Customer {data.customer_id} not found or inactive")
        quotation.customer_id = data.customer_id

    # Update quotation fields
    if data.notes is not None:
        quotation.notes = data.notes
    if data.description is not None:
        quotation.description = data.description

    # Handle items
    if data.items:
        existing_items = {item.id: item for item in quotation.items if not item.is_deleted}

        for item_data in data.items:
            if item_data.id is not None:
                # Update or delete existing item
                item = existing_items.get(item_data.id)
                if not item:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Quotation item with id {item_data.id} not found. Existing IDs: {list(existing_items.keys())}"
                    )

                if item_data.is_deleted:
                    if quotation.moved_to_sales or quotation.moved_to_invoice:
                        raise HTTPException(
                            status_code=400,
                            detail="Cannot delete item from a quotation already moved to sales or invoice"
                        )
                    item.is_deleted = True
                    item.updated_by = current_user.id
                else:
                    if item_data.quantity is not None:
                        if item_data.quantity <= 0:
                            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
                        item.quantity = item_data.quantity
                        item.total = round(item.quantity * item.unit_price, 2)
                        item.updated_by = current_user.id

            else:
                # Add new item
                if not item_data.product_id:
                    raise HTTPException(status_code=400, detail="Product ID is required for new items")
                product = await db.get(Product, item_data.product_id)
                if not product or product.is_deleted:
                    raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")
                if any(item.product_id == product.id and not item.is_deleted for item in quotation.items):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product '{product.name}' is already added to this quotation"
                    )
                if not item_data.quantity or item_data.quantity <= 0:
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

    # Update totals and audit
    quotation.calculate_totals()
    quotation.updated_by = current_user.id
    db.add(quotation)

    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Quotation '{quotation.quotation_number}' updated by '{current_user.username}'"
    )

    await db.commit()
    await db.refresh(quotation)

    quotation.items = [item for item in quotation.items if not item.is_deleted]

    return QuotationResponse(
        message="Quotation updated successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# SOFT DELETE QUOTATION
# --------------------------
async def delete_quotation(db: AsyncSession, quotation_id: int, deleted_by: Optional[int] = None) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales:
        raise HTTPException(status_code=400, detail="Cannot delete a quotation moved to sales order")

    quotation.is_deleted = True
    quotation.updated_by = deleted_by
    await db.commit()
    return QuotationResponse(message="Quotation deleted successfully", data=None)


# --------------------------
# APPROVE QUOTATION
# --------------------------
async def approve_quotation(db: AsyncSession, quotation_id: int, approved_by: Optional[int] = None) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation already approved")

    quotation.approved = True
    quotation.updated_by = approved_by
    await db.commit()
    await db.refresh(quotation)

    return QuotationResponse(
        message="Quotation approved successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# MOVE QUOTATION TO SALES
# --------------------------
async def move_to_sales(db: AsyncSession, quotation_id: int, moved_by: Optional[int] = None) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_sales:
        raise HTTPException(status_code=400, detail="Quotation already moved to sales order")
    if not quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation must be approved before moving to sales")

    quotation.moved_to_sales = True
    quotation.updated_by = moved_by
    await db.commit()
    await db.refresh(quotation)

    return QuotationResponse(
        message="Quotation moved to sales successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# MOVE QUOTATION TO INVOICE
# --------------------------
async def move_to_invoice(db: AsyncSession, quotation_id: int, moved_by: Optional[int] = None) -> QuotationResponse:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation or quotation.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.moved_to_invoice:
        raise HTTPException(status_code=400, detail="Quotation already moved to invoice")
    if not quotation.approved:
        raise HTTPException(status_code=400, detail="Quotation must be approved or moved to sales before invoicing")

    quotation.moved_to_invoice = True
    quotation.updated_by = moved_by
    await db.commit()
    await db.refresh(quotation)

    return QuotationResponse(
        message="Quotation moved to invoice successfully",
        data=QuotationOut.from_orm(quotation)
    )


# --------------------------
# DELETE QUOTATION ITEM (soft delete)
# --------------------------
async def delete_quotation_item(db: AsyncSession, item_id: int, deleted_by: Optional[int] = None) -> QuotationResponse:
    item = await db.get(QuotationItem, item_id)
    if not item or item.is_deleted:
        raise HTTPException(status_code=404, detail="Quotation item not found")
    if item.quotation.moved_to_sales:
        raise HTTPException(status_code=400, detail="Cannot delete item from a quotation already moved to sales")

    item.is_deleted = True
    item.updated_by = deleted_by
    await db.commit()
    await db.refresh(item.quotation)

    return QuotationResponse(
        message="Quotation item deleted successfully",
        data=QuotationOut.from_orm(item.quotation)
    )

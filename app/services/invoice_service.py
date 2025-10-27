# app/services/invoice_service.py

import datetime
import random
import string
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    select, update, or_, not_, exists, and_
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.invoice_models import Invoice, Payment, LoyaltyToken, InvoiceStatus
from app.models import SalesOrder, Quotation
from app.schemas.invoice_schemas import InvoiceResponse, Approve
from app.utils.decimal_utils import to_decimal
from app.utils.activity_helpers import log_user_activity




# -------------------------------------------------------------------------
# Helper: Generate Unique Invoice Number
# -------------------------------------------------------------------------
async def _generate_invoice_number(session: AsyncSession, prefix: str = "INV"):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{ts}-{suffix}"


# -------------------------------------------------------------------------
# Fetch Quotations & Sales Orders Ready for Invoice
# -------------------------------------------------------------------------
async def get_ready_to_invoice(db: AsyncSession):
    # Get quotations ready for invoice
    q_stmt = (
        select(Quotation)
        .where(Quotation.moved_to_sales == True)
        .where(Quotation.moved_to_invoice == False)
        .where(Quotation.approved == True)
        .where(not_(exists().where(Invoice.quotation_id == Quotation.id)))
    )
    q_result = await db.execute(q_stmt)
    quotations = q_result.unique().scalars().all()

    quotations_data = []
    for q in quotations:
        items_data = [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
            }
            for item in q.items if not item.is_deleted
        ]
        quotations_data.append({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "customer_id": q.customer_id,
            "total_items_amount": q.total_items_amount,
            "gst_amount": q.gst_amount,
            "total_amount": q.total_amount,
            "items": items_data,
        })

    # Get sales orders ready for invoice
    s_stmt = (
        select(SalesOrder)
        .where(SalesOrder.approved == True)
        .where(SalesOrder.moved_to_invoice == True)
        .where(not_(exists().where(Invoice.sales_order_id == SalesOrder.id)))
    )
    s_result = await db.execute(s_stmt)
    sales_orders = s_result.unique().scalars().all()

    sales_orders_data = []
    for so in sales_orders:
        total_amount = Decimal("0.00")
        if so.quotation_snapshot:
            for item in so.quotation_snapshot:
                total_amount += Decimal(str(item.get("total", 0)))
            gst = total_amount * Decimal("0.18")
            total_amount += gst
        sales_orders_data.append({
            "id": so.id,
            "customer_id": so.customer_id,
            "quotation_id": so.quotation_id,
            "quotation_snapshot": so.quotation_snapshot,
            "total_amount": total_amount,
            "customer_name": so.customer_name,
        })

    return {
        "quotations": quotations_data,
        "sales_orders": sales_orders_data,
    }


# -------------------------------------------------------------------------
# Create Invoice
# -------------------------------------------------------------------------
async def create_invoice(
    _user,
    session: AsyncSession,
    *,
    quotation_id: int = None,
    sales_order_id: int = None,
) -> Invoice:
    if not quotation_id and not sales_order_id:
        raise ValueError("Either quotation_id or sales_order_id must be provided")

    # Prevent duplicates
    conditions = []
    if quotation_id:
        conditions.append(Invoice.quotation_id == quotation_id)
    if sales_order_id:
        conditions.append(Invoice.sales_order_id == sales_order_id)

    if conditions:
        stmt = select(Invoice).where(or_(*conditions))
        result = await session.execute(stmt)
        if result.scalars().first():
            raise ValueError("Invoice already exists for this quotation or sales order")

    # Retrieve linked quotation/sales order
    if quotation_id:
        result = await session.execute(select(Quotation).where(Quotation.id == quotation_id))
        quotation = result.unique().scalar_one_or_none()
        if not quotation:
            raise ValueError("Quotation not found")
        customer_id = quotation.customer_id
        total_amount = quotation.total_amount

    elif sales_order_id:
        result = await session.execute(select(SalesOrder).where(SalesOrder.id == sales_order_id))
        sales_order = result.unique().scalar_one_or_none()
        if not sales_order:
            raise ValueError("Sales order not found")
        if not sales_order.quotation_id:
            raise ValueError("Sales order does not have a linked quotation")

        result = await session.execute(select(Quotation).where(Quotation.id == sales_order.quotation_id))
        quotation = result.unique().scalar_one_or_none()
        if not quotation:
            raise ValueError("Linked quotation not found for this sales order")

        customer_id = quotation.customer_id
        total_amount = quotation.total_amount
        quotation_id = quotation.id

    total_amount = to_decimal(total_amount)

    for _ in range(5):
        invoice_number = await _generate_invoice_number(session)
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=customer_id,
            quotation_id=quotation_id,
            sales_order_id=sales_order_id,
            total_amount=total_amount,
            discounted_amount=Decimal("0.00"),
            total_paid=Decimal("0.00"),
            balance_due=total_amount,
            status=InvoiceStatus.PENDING,
        )
        session.add(invoice)
        try:
            await session.flush()
            await log_user_activity(
                db=session,
                user_id=_user.id,
                username=_user.username,
                message=(
                    f"Created Invoice '{invoice_number}' for Customer ID '{customer_id}', "
                    f"linked to Quotation ID '{quotation_id}' and Sales Order ID '{sales_order_id}'. "
                    f"Total Amount: ₹{total_amount:.2f}"
                ),
            )
            await session.commit()
            return invoice
        except IntegrityError:
            await session.rollback()
            continue

    raise RuntimeError("Could not generate unique invoice number after retries")


# -------------------------------------------------------------------------
# Apply Discount
# -------------------------------------------------------------------------
async def apply_discount(
    _user,
    session: AsyncSession,
    invoice_id: int,
    discount_amount: Decimal,
    note: str = None,
) -> InvoiceResponse:
    discount_amount = to_decimal(discount_amount)
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise ValueError("Invoice not found")

    if invoice.discounted_amount > Decimal("0.00"):
        raise ValueError("Discount has already been applied to this invoice")
    if invoice.status == InvoiceStatus.PAID:
        raise ValueError("Cannot apply discount to a paid invoice")
    if discount_amount < 0:
        raise ValueError("Discount must be non-negative")
    if discount_amount > invoice.total_amount:
        raise ValueError("Discount cannot exceed invoice total")

    invoice.discounted_amount = discount_amount
    invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)
    if invoice.balance_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID
    elif invoice.total_paid > Decimal("0.00"):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = InvoiceStatus.PENDING

    await log_user_activity(
        db=session,
        user_id=_user.id,
        username=_user.username,
        message=f"Applied discount of ₹{discount_amount:.2f} to Invoice ID {invoice.id}",
    )

    await session.commit()
    await session.refresh(invoice)
    return InvoiceResponse.model_validate(invoice, from_attributes=True)


# -------------------------------------------------------------------------
# Approve Invoice
# -------------------------------------------------------------------------
async def approve_invoice(_user, session: AsyncSession, invoice_id: int, payload: Approve):
    r = await session.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    invoice = r.unique().scalar_one_or_none()

    if invoice is None:
        raise ValueError("Invoice not found")
    if invoice.approved_by_admin:
        raise ValueError("Invoice already approved")
    if to_decimal(invoice.total_amount) <= Decimal("0.00"):
        raise ValueError("Cannot approve invoice with zero total")

    if payload.discount_amount is not None:
        discount_amount = to_decimal(payload.discount_amount)
        if discount_amount < 0 or discount_amount > invoice.total_amount:
            raise ValueError("Invalid discount amount")
        invoice.discounted_amount = discount_amount
        invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)

    invoice.approved_by_admin = True
    invoice.status = InvoiceStatus.APPROVED

    await log_user_activity(
        db=session,
        user_id=_user.id,
        username=_user.username,
        message=f"Approved Invoice ID {invoice.id} with total ₹{invoice.total_amount:.2f}",
    )

    await session.commit()
    await session.refresh(invoice)
    return invoice


# -------------------------------------------------------------------------
# Add Payment
# -------------------------------------------------------------------------
async def add_payment(
    _user,
    session: AsyncSession,
    invoice_id: int,
    amount: Decimal,
    payment_method: str = None,
) -> Payment:
    amount = to_decimal(amount)
    if amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be positive")

    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    invoice = result.unique().scalar_one_or_none()
    if invoice is None:
        raise ValueError("Invoice not found")
    if not invoice.approved_by_admin:
        raise ValueError("Invoice not Approved")

    balance = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)
    if amount > balance:
        raise ValueError(f"Payment exceeds balance. Max allowed: {balance}")

    payment = Payment(
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=amount,
        payment_method=payment_method,
    )
    session.add(payment)

    invoice.total_paid = to_decimal(invoice.total_paid + amount)
    invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)
    invoice.status = (
        InvoiceStatus.PAID if invoice.balance_due == Decimal("0.00")
        else InvoiceStatus.PARTIALLY_PAID
    )

    await log_user_activity(
        db=session,
        user_id=_user.id,
        username=_user.username,
        message=f"Added payment of ₹{amount:.2f} to Invoice ID {invoice.id}. New balance: ₹{invoice.balance_due:.2f}",
    )

    await session.commit()
    await session.refresh(payment)
    return payment


# -------------------------------------------------------------------------
# Loyalty Token Generation
# -------------------------------------------------------------------------
async def award_loyalty_for_invoice(
    _user,
    session: AsyncSession,
    invoice_id: int,
    token_rate_per_1000: int = 1,
):
    """
    Awards loyalty tokens to the customer for a fully paid invoice.
    - Only executes if invoice status == PAID and loyalty not already claimed.
    - 1 token per 1000 units of currency by default.
    """
    # Lock invoice row for safe update
    result = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    )
    invoice = result.unique().scalar_one_or_none()

    if invoice is None or invoice.loyalty_claimed or invoice.status != InvoiceStatus.PAID:
        return None

    total_amount = to_decimal(invoice.total_amount)
    tokens = int((total_amount // Decimal("1000")) * token_rate_per_1000)
    lt = None

    if tokens > 0:
        lt = LoyaltyToken(
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            tokens=tokens,
        )
        session.add(lt)

    # Mark invoice as loyalty claimed
    invoice.loyalty_claimed = True
    await session.flush()

    # ✅ Commit to persist both invoice and loyalty token changes
    await session.commit()

    return lt if tokens > 0 else None



# -------------------------------------------------------------------------
# Invoice Queries
# -------------------------------------------------------------------------
async def get_all_invoices(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Fetch invoices with optional filters."""
    stmt = select(Invoice)

    if status:
        stmt = stmt.where(Invoice.status == status)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if date_from and date_to:
        stmt = stmt.where(Invoice.created_at.between(date_from, date_to))

    stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    return result.unique().scalars().all()


async def get_invoice_by_id(session: AsyncSession, invoice_id: int) -> Optional[Invoice]:
    res = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    return res.unique().scalar_one_or_none()


async def get_invoices_by_customer(
    session: AsyncSession,
    customer_id: int,
    limit: int = 100,
    offset: int = 0,
):
    res = await session.execute(
        select(Invoice)
        .where(Invoice.customer_id == customer_id)
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return res.unique().scalars().all()


# -------------------------------------------------------------------------
# Final Bill Summary
# -------------------------------------------------------------------------
async def get_final_bill(session: AsyncSession, invoice_id: int) -> dict:
    r = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = r.unique().scalar_one_or_none()
    if invoice is None:
        raise ValueError("Invoice not found")

    subtotal = to_decimal(invoice.total_amount)
    discount = to_decimal(invoice.discounted_amount)
    total_paid = to_decimal(invoice.total_paid)
    balance = to_decimal(invoice.balance_due)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "subtotal": str(subtotal),
        "discount": str(discount),
        "total_paid": str(total_paid),
        "balance_due": str(balance),
        "status": invoice.status.value,
    }


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.invoice_models import Payment


async def get_all_payments(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    customer_id: Optional[int] = None,
    invoice_id: Optional[int] = None
) -> List[Payment]:
    """
    Fetch all payments with optional filters for customer or invoice.
    Supports pagination.
    """
    query = select(Payment)

    if customer_id:
        query = query.where(Payment.customer_id == customer_id)
    if invoice_id:
        query = query.where(Payment.invoice_id == invoice_id)

    query = query.order_by(Payment.payment_date.desc()).limit(limit).offset(offset)

    res = await session.execute(query)
    return res.unique().scalars().all()



async def get_payment_by_id(session: AsyncSession, payment_id: int):
    res = await session.execute(select(Payment).where(Payment.id == payment_id))
    return res.unique().scalar_one_or_none()

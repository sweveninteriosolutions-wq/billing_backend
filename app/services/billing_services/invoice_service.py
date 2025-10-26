# app\services\billing_services\invoice_service.py
from sqlalchemy import select, update, or_, not_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from app.models.invoice_models import Invoice, Payment, LoyaltyToken, InvoiceStatus
from app.utils.decimal_utils import to_decimal
import datetime
import random
import string
from app.models import SalesOrder, Quotation
from sqlalchemy.orm import selectinload
from app.schemas.invoice_schemas import InvoiceResponse, Approve

async def _generate_invoice_number(session: AsyncSession, prefix="INV"):
    # quick generator, small random suffix; collisions handled by retry
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{ts}-{suffix}"

async def get_ready_to_invoice(db: AsyncSession):
    # Get quotations ready for invoice
    q_stmt = (
        select(Quotation)
        .where(Quotation.moved_to_sales == True)
        .where(Quotation.moved_to_invoice == False)
        .where(Quotation.approved == True)
        .where(
            not_(
                exists().where(Invoice.quotation_id == Quotation.id)
            )
        )
    )
    q_result = await db.execute(q_stmt)
    quotations = q_result.unique().scalars().all()

    # Convert to structured response
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
            "items": items_data
        })

    # Get sales orders ready for invoice
    s_stmt = (
        select(SalesOrder)
        .where(SalesOrder.approved == True)
        .where(SalesOrder.moved_to_invoice == True)
        .where(
            not_(
                exists().where(Invoice.sales_order_id == SalesOrder.id)
            )
        )
    )
    s_result = await db.execute(s_stmt)
    sales_orders = s_result.unique().scalars().all()

    sales_orders_data = []
    for so in sales_orders:
        total_amount = Decimal("0.00")
        if so.quotation_snapshot:
            # calculate total from quotation snapshot
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
            "customer_name": so.customer_name
        })

    return {
        "quotations": quotations_data,
        "sales_orders": sales_orders_data
    }

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

async def create_invoice(
    session: AsyncSession,
    *,
    quotation_id: int = None,
    sales_order_id: int = None
) -> Invoice:
    if not quotation_id and not sales_order_id:
        raise ValueError("Either quotation_id or sales_order_id must be provided")
    
    conditions = []
    if quotation_id:
        conditions.append(Invoice.quotation_id == quotation_id)
    if sales_order_id:
        conditions.append(Invoice.sales_order_id == sales_order_id)

    if conditions:
        stmt = select(Invoice).where(or_(*conditions))
        result = await session.execute(stmt)
        existing_invoice = result.scalars().first()
        if existing_invoice:
            raise ValueError("Invoice already exists for this quotation or sales order")
        
    if quotation_id:
        # fetch quotation details
        result = await session.execute(
            select(Quotation).where(Quotation.id == quotation_id)
        )
        quotation = result.unique().scalar_one_or_none()
        if not quotation:
            raise ValueError("Quotation not found")
        customer_id = quotation.customer_id
        total_amount = quotation.total_amount
    
    elif sales_order_id:
        # fetch sales order
        result = await session.execute(select(SalesOrder).where(SalesOrder.id == sales_order_id))
        sales_order = result.unique().scalar_one_or_none()
        if not sales_order:
            raise ValueError("Sales order not found")

        if not sales_order.quotation_id:
            raise ValueError("Sales order does not have a linked quotation")

        # fetch the linked quotation
        result = await session.execute(select(Quotation).where(Quotation.id == sales_order.quotation_id))
        quotation = result.unique().scalar_one_or_none()
        if not quotation:
            raise ValueError("Linked quotation not found for this sales order")

        customer_id = quotation.customer_id
        total_amount = quotation.total_amount
        quotation_id = quotation.id  # ensure invoice links back to the quotation

    total_amount = to_decimal(total_amount)
    # try generating unique invoice number
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
            status=InvoiceStatus.PENDING
        )
        session.add(invoice)
        try:
            await session.flush()  # attempt insert
            await session.commit() 
            return invoice
        except IntegrityError:
            await session.rollback()
            continue

    raise RuntimeError("Could not generate unique invoice number after retries")


async def get_all_invoices(session: AsyncSession, limit: int = 100, offset: int = 0):
    q = select(Invoice).order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    res = await session.execute(q)
    return res.scalars().all()

async def get_invoice_by_id(session: AsyncSession, invoice_id: int) -> Invoice | None:
    res = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    return res.scalar_one_or_none()

async def get_invoices_by_customer(session: AsyncSession, customer_id: int, limit: int=100, offset:int=0):
    res = await session.execute(select(Invoice).where(Invoice.customer_id == customer_id).order_by(Invoice.created_at.desc()).limit(limit).offset(offset))
    return res.scalars().all()



async def apply_discount(
    session: AsyncSession,
    invoice_id: int,
    discount_amount: Decimal,
    note: str = None
) -> InvoiceResponse:
    # Convert input to Decimal
    discount_amount = to_decimal(discount_amount)

    # Fetch the invoice (row-level lock optional)
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer))
        .where(Invoice.id == invoice_id)
        # .with_for_update()  # optional; remove if you don't want a lock
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ValueError("Invoice not found")
    
        # Check if discount was already applied
    if invoice.discounted_amount > Decimal("0.00"):
        raise ValueError("Discount has already been applied to this invoice")

    # Validation
    if invoice.status == InvoiceStatus.PAID:
        raise ValueError("Cannot apply discount to a paid invoice")
    if discount_amount < 0:
        raise ValueError("Discount must be non-negative")
    if discount_amount > invoice.total_amount:
        raise ValueError("Discount cannot exceed invoice total")

    # Apply discount
    invoice.discounted_amount = discount_amount
    invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)

    # Adjust invoice status
    if invoice.balance_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID
    elif invoice.total_paid > Decimal("0.00"):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = InvoiceStatus.PENDING

    # Commit changes to DB immediately
    await session.commit()

    # Convert to Pydantic model for response
    await session.refresh(invoice)
    invoice_response = InvoiceResponse.model_validate(invoice, from_attributes=True)


    return invoice_response




async def approve_invoice(session: AsyncSession, invoice_id: int, payload: Approve):
    async with session.begin():
        # Lock the invoice row
        r = await session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .with_for_update()
        )
        invoice = r.scalar_one_or_none()
        if invoice is None:
            raise ValueError("Invoice not found")
        
        # Prevent double approval
        if invoice.approved_by_admin:
            raise ValueError("Invoice already approved")
        
        # Prevent approving invoices with zero total
        if to_decimal(invoice.total_amount) <= Decimal("0.00"):
            raise ValueError("Cannot approve invoice with zero total")

        # ---- APPLY OR UPDATE DISCOUNT IF PROVIDED ----
        if payload.discount_amount is not None:
            discount_amount = to_decimal(payload.discount_amount)
            
            # Validation
            if discount_amount < 0:
                raise ValueError("Discount must be non-negative")
            if discount_amount > invoice.total_amount:
                raise ValueError("Discount cannot exceed invoice total")
            
            # Apply discount
            invoice.discounted_amount = discount_amount
            invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)

        # ---- UPDATE INVOICE STATUS ----
        invoice.approved_by_admin = True
        invoice.status = InvoiceStatus.APPROVED

        await session.flush()
        await session.refresh(invoice)

        return invoice


async def get_final_bill(session: AsyncSession, invoice_id: int) -> dict:
    r = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = r.scalar_one_or_none()
    if invoice is None:
        raise ValueError("Invoice not found")
    # compute breakdown
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
        "status": invoice.status.value
    }


async def add_payment(
    session: AsyncSession,
    invoice_id: int,
    customer_id: int,
    amount: Decimal,
    payment_method: str = None
) -> Payment:
    amount = to_decimal(amount)
    if amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be positive")

    # ✅ Don't start a new transaction; rely on FastAPI's managed session
    result = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise ValueError("Invoice not found")

    if invoice.customer_id != customer_id:
        raise ValueError("Payment customer mismatch")

    # compute final accepted amount (cannot exceed balance due)
    balance = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)
    if amount > balance:
        raise ValueError(f"Payment exceeds balance. Max allowed: {balance}")

    # ✅ Create payment record
    payment = Payment(
        invoice_id=invoice.id,
        customer_id=customer_id,
        amount=amount,
        payment_method=payment_method
    )
    session.add(payment)

    # ✅ Update invoice totals and status
    invoice.total_paid = to_decimal(invoice.total_paid + amount)
    invoice.balance_due = to_decimal(invoice.total_amount - invoice.discounted_amount - invoice.total_paid)

    if invoice.balance_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    await session.commit()  # ✅ Commit here to make DB changes permanent
    await session.refresh(payment)

    # Loyalty awarding should happen after commit (in router or service layer)
    return payment

async def get_all_payments(session: AsyncSession, limit:int=100, offset:int=0):
    res = await session.execute(select(Payment).order_by(Payment.payment_date.desc()).limit(limit).offset(offset))
    return res.scalars().all()

async def get_payment_by_id(session: AsyncSession, payment_id: int):
    res = await session.execute(select(Payment).where(Payment.id == payment_id))
    return res.scalar_one_or_none()

async def award_loyalty_for_invoice(session: AsyncSession, invoice_id: int, token_rate_per_1000: int = 1):
    r = await session.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    invoice = r.scalar_one_or_none()
    if invoice is None or invoice.loyalty_claimed or invoice.status != InvoiceStatus.PAID:
        return None

    total_amount = to_decimal(invoice.total_amount)
    tokens = int((total_amount // Decimal("1000")) * token_rate_per_1000)
    if tokens > 0:
        lt = LoyaltyToken(customer_id=invoice.customer_id, invoice_id=invoice.id, tokens=tokens)
        session.add(lt)
    invoice.loyalty_claimed = True

    await session.flush()  # ✅ flush is enough if the parent transaction commits
    return lt if tokens > 0 else None


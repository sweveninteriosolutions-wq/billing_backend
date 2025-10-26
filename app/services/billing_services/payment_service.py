# app/services/billing/payment_service.py
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.billing_models.invoice_models import Invoice, InvoiceStatus
from app.models.billing_models.invoice_models import Payment  # your model
from app.utils.decimal_utils import to_decimal, compute_balance

async def add_payment(session: AsyncSession, invoice_id: int, customer_id: int, amount: Decimal, payment_method: str) -> Payment:
    amount = to_decimal(amount)
    if amount <= Decimal("0.00"):
        raise ValueError("Payment must be greater than zero")

    async with session.begin():
        # lock invoice row
        r = await session.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
        inv: Invoice = r.scalar_one_or_none()
        if not inv:
            raise ValueError("Invoice not found")

        # verify customer matches
        if inv.customer_id != customer_id:
            raise ValueError("Customer ID does not match invoice")

        # compute current balance and prevent overpayment
        current_balance = compute_balance(inv.total_amount, inv.discounted_amount, inv.total_paid)
        if amount > current_balance:
            raise ValueError(f"Payment exceeds balance due. Balance: {current_balance}, attempted: {amount}")

        # create payment
        payment = Payment(invoice_id=inv.id, customer_id=customer_id, amount=amount, payment_method=payment_method)
        session.add(payment)

        # update invoice aggregates
        inv.total_paid = to_decimal(inv.total_paid + amount)
        inv.balance_due = compute_balance(inv.total_amount, inv.discounted_amount, inv.total_paid)

        # update status
        if inv.balance_due == Decimal("0.00"):
            inv.status = InvoiceStatus.PAID
        elif inv.total_paid > Decimal("0.00"):
            inv.status = InvoiceStatus.PARTIALLY_PAID
        else:
            inv.status = InvoiceStatus.PENDING

        await session.flush()
        return payment

async def get_all_payments(session: AsyncSession, limit: int = 100, offset: int = 0):
    res = await session.execute(select(Payment).order_by(Payment.payment_date.desc()).limit(limit).offset(offset))
    return res.scalars().all()

async def get_payment_by_id(session: AsyncSession, payment_id: int):
    res = await session.execute(select(Payment).where(Payment.id == payment_id))
    return res.scalar_one_or_none()

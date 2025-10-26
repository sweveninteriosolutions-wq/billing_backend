# app/services/billing/loyalty_service.py
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.billing_models.invoice_models import Invoice
from app.models.billing_models.invoice_models import LoyaltyToken  # your model
from app.utils.decimal_utils import to_decimal

# Example rule: 1 token per 1000 units of total_amount
TOKEN_RATE_BASE = Decimal("1000")

async def award_loyalty_for_invoice(session: AsyncSession, invoice_id: int, token_rate_multiplier: int = 1):
    async with session.begin():
        r = await session.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
        inv: Invoice = r.scalar_one_or_none()
        if not inv:
            raise ValueError("Invoice not found")
        if inv.loyalty_claimed:
            return None  # already awarded
        # require paid invoice
        if inv.status != 'PAID':
            raise ValueError("Invoice not fully paid; cannot award loyalty tokens")

        # compute tokens
        amt = to_decimal(inv.total_amount)
        tokens = int((amt // TOKEN_RATE_BASE) * token_rate_multiplier)
        if tokens <= 0:
            inv.loyalty_claimed = True
            await session.flush()
            return None

        token_obj = LoyaltyToken(customer_id=inv.customer_id, invoice_id=inv.id, tokens=tokens)
        session.add(token_obj)
        inv.loyalty_claimed = True
        await session.flush()
        return token_obj

async def get_all_loyalty_tokens(session: AsyncSession, limit: int = 100, offset: int = 0):
    res = await session.execute(select(LoyaltyToken).order_by(LoyaltyToken.created_at.desc()).limit(limit).offset(offset))
    return res.scalars().all()

async def get_loyalty_by_id(session: AsyncSession, token_id: int):
    res = await session.execute(select(LoyaltyToken).where(LoyaltyToken.id == token_id))
    return res.scalar_one_or_none()

async def get_loyalty_by_customer(session: AsyncSession, customer_id: int, limit: int = 100, offset: int = 0):
    res = await session.execute(select(LoyaltyToken).where(LoyaltyToken.customer_id == customer_id).order_by(LoyaltyToken.created_at.desc()).limit(limit).offset(offset))
    return res.scalars().all()

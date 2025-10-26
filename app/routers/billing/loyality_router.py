# app/api/routers/loyalty.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.services.billing_services.loyalty_service import award_loyalty_for_invoice
from app.models.billing_models.invoice_models import LoyaltyToken
from app.schemas.billing_schemas.invoice_schemas import LoyaltyTokenResponse, LoyaltySummaryResponse
from app.core.db import get_db
from app.services.billing_services.invoice_service import get_invoice_by_id
from sqlalchemy import select

router = APIRouter()

@router.get("/loyalty/{token_id}", response_model=LoyaltyTokenResponse, tags=["loyalty"])
async def get_loyalty_by_id(token_id: int, session: AsyncSession = Depends(get_db)):
    r = await session.execute(select(LoyaltyToken).where(LoyaltyToken.id == token_id))
    tok = r.scalar_one_or_none()
    if not tok:
        raise HTTPException(status_code=404, detail="Token not found")
    return tok  # Pydantic will safely convert ORM to JSON

from typing import List

from sqlalchemy import func

@router.get("/loyalty/customer/{customer_id}", response_model=LoyaltySummaryResponse, tags=["loyalty"])
async def get_loyalty_by_customer(customer_id: int, session: AsyncSession = Depends(get_db)):

    # Fetch all tokens for customer
    r = await session.execute(
        select(LoyaltyToken)
        .where(LoyaltyToken.customer_id == customer_id)
        .order_by(LoyaltyToken.created_at.desc())
    )
    tokens = r.scalars().all()

    # Convert ORM objects to Pydantic models
    tokens_response = [LoyaltyTokenResponse.model_validate(tok, from_attributes=True) for tok in tokens]

    # Aggregate total tokens and transactions
    r_total = await session.execute(
        select(func.coalesce(func.sum(LoyaltyToken.tokens), 0), func.count(LoyaltyToken.id))
        .where(LoyaltyToken.customer_id == customer_id)
    )
    total_tokens, total_transactions = r_total.one()

    return LoyaltySummaryResponse(
        total_tokens=int(total_tokens),
        total_transactions=total_transactions,
        tokens=tokens_response
    )

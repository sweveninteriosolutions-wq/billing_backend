# app/api/routers/payments.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.billing_services.invoice_service import get_all_payments, get_payment_by_id
from app.schemas.invoice_schemas import PaymentResponse
from app.core.db import get_db
from app.utils.check_roles import require_role


router = APIRouter()

@router.get("/payments", response_model=List[PaymentResponse], tags=["Payments"])
@require_role(["admin", "cashier"])
async def route_get_payments(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    payments = await get_all_payments(session, limit=limit, offset=offset)
    return payments

@router.get("/payments/{payment_id}", response_model=PaymentResponse, tags=["Payments"])
@require_role(["admin", "cashier"])
async def route_get_payment(payment_id: int, session: AsyncSession = Depends(get_db)):
    p = await get_payment_by_id(session, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    return p

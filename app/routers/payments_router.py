# app/routers/payments.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.invoice_service import get_all_payments, get_payment_by_id
from app.schemas.invoice_schemas import PaymentResponse
from app.core.db import get_db
from app.utils.check_roles import require_role
from typing import Optional
from app.utils.get_user import get_current_user


router = APIRouter()

@router.get("/payments", response_model=List[PaymentResponse])
@require_role(["admin", "cashier"])
async def route_get_payments(
    limit: int = 100,
    offset: int = 0,
    customer_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    """
    Retrieve all payments with optional filters for customer or invoice.
    Supports pagination.
    """
    payments = await get_all_payments(
        session,
        limit=limit,
        offset=offset,
        customer_id=customer_id,
        invoice_id=invoice_id
    )
    return payments


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
@require_role(["admin", "cashier"])
async def route_get_payment(payment_id: int, session: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """
    Retrieve a single payment by ID.
    """
    payment = await get_payment_by_id(session, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
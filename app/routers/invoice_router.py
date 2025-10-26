# app/api/routers/invoices.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from decimal import Decimal
from typing import List
from app.schemas.invoice_schemas import (InvoiceCreate, InvoiceResponse, PaymentCreate,
                                        DiscountApply, ApproveResponse, ReadyToInvoiceResponse,Approve, PaymentResponse)
from app.services.billing_services.invoice_service import (create_invoice, get_all_invoices, get_invoice_by_id,
                                    get_invoices_by_customer, apply_discount, approve_invoice,
                                    get_final_bill, add_payment, award_loyalty_for_invoice, get_ready_to_invoice)
from app.utils.get_user import get_current_user
from app.utils.activity_helpers import log_user_activity
from app.utils.check_roles import require_role

router = APIRouter(prefix="/billing", tags=["Invoice"]) 

# GET /billing/invoices/available
@router.get("/invoices/ready", response_model=ReadyToInvoiceResponse)
@require_role(["admin", "cashier"])
async def route_get_ready_to_invoice(db: AsyncSession = Depends(get_db)):
    """
    Get all quotations and sales orders that are ready to generate an invoice.
    - Quotation: approved, moved_to_sales=True, moved_to_invoice=False
    - SalesOrder: approved, moved_to_invoice=False
    """
    data = await get_ready_to_invoice(db)
    return data

# POST /billing/invoices
@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
@require_role(["admin", "cashier"])
async def route_create_invoice(payload: InvoiceCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    try:
        invoice = await create_invoice(_user, db, quotation_id=payload.quotation_id, sales_order_id=payload.sales_order_id)
        return invoice
    except ValueError  as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/invoices", response_model=List[InvoiceResponse])
@require_role(["admin", "cashier"])
async def route_get_all_invoices(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    invoices = await get_all_invoices(db, limit=limit, offset=offset)
    return invoices


# GET /billing/invoices/{invoice_id}
@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
@require_role(["admin", "cashier"])
async def route_get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    invoice = await get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

# GET /billing/invoices/customer/{customer_id}
@router.get("/invoices/customer/{customer_id}", response_model=List[InvoiceResponse])
@require_role(["admin", "cashier"])
async def route_invoices_by_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    invoices = await get_invoices_by_customer(db, customer_id)
    return invoices


# POST /billing/invoices/{invoice_id}/discount
@router.post("/invoices/{invoice_id}/discount", response_model=InvoiceResponse)
@require_role(["admin", "cashier"])
async def route_apply_discount(invoice_id: int, payload: DiscountApply, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    try:
        inv = await apply_discount(_user, db, invoice_id, payload.discount_amount, note=payload.note)
        return inv
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# POST /billing/invoices/{invoice_id}/approve
@require_role(["admin"])
@router.post("/invoices/{invoice_id}/approve", response_model=ApproveResponse)
async def route_approve_invoice(invoice_id: int, payload: Approve, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    try:
        inv = await approve_invoice(_user, db, invoice_id,  payload)
        return {"id": inv.id, "status": inv.status, "approved_by_admin": inv.approved_by_admin}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# GET /billing/invoices/{invoice_id}/bill
@router.get("/invoices/{invoice_id}/bill")
@require_role(["admin", "cashier"])
async def route_get_bill(invoice_id: int, db: AsyncSession = Depends(get_db)):
    try:
        bill = await get_final_bill(db, invoice_id)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# POST /billing/payments/{invoice_id}
@router.post("/payments/{invoice_id}", response_model=PaymentResponse)
@require_role(["admin", "cashier"])
async def route_add_payment(invoice_id: int, payload: PaymentCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    # user must be the customer paying; or you can allow admin to add payments on behalf
    try:
        payment = await add_payment(_user, db, invoice_id=invoice_id, amount=payload.amount, payment_method=payload.payment_method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # After transaction commit, attempt to award loyalty (we can call the award function)
    try:
        # award_loyalty_for_invoice will be executed in a transaction; since add_payment already committed,
        # we call award which will start its own transaction.
        await award_loyalty_for_invoice(_user, db, invoice_id=invoice_id)
                # ✅ Logging activity
        await log_user_activity(
            db=db,
            user_id=_user.id,
            username=_user.username,
            message=f"Awarded loyalty tokens to Customer for Invoice"
        )
        await db.commit() 

    except Exception:
        # don't block payment success on loyalty issues
        pass
    return payment

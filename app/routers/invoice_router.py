# app/routers/invoice_routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
from decimal import Decimal
from typing import List, Optional

from app.core.db import get_db
from app.schemas.invoice_schemas import (
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    DiscountApply,
    ApproveResponse,
    ReadyToInvoiceResponse,
    Approve,
    PaymentResponse
)
from app.services.invoice_service import (
    create_invoice,
    get_all_invoices,
    get_invoice_by_id,
    get_invoices_by_customer,
    apply_discount,
    approve_invoice,
    get_final_bill,
    add_payment,
    award_loyalty_for_invoice,
    get_ready_to_invoice
)
from app.utils.get_user import get_current_user
from app.utils.activity_helpers import log_user_activity
from app.utils.check_roles import require_role
from app.utils.pdf_generators.invoice_pdf import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["Invoice"])


# ------------------------------------------------------------
# GET /billing/ready
# ------------------------------------------------------------
@router.get("/ready", response_model=ReadyToInvoiceResponse)
@require_role(["admin", "cashier"])
async def route_get_ready_to_invoice(
    db: AsyncSession = Depends(get_db),
    *,
    _user=Depends(get_current_user)  # keyword-only argument required by @require_role
):
    """
    Get all quotations and sales orders that are ready to generate an invoice.
    - Quotation: approved, moved_to_sales=True, moved_to_invoice=False
    - SalesOrder: approved, moved_to_invoice=False
    """
    data = await get_ready_to_invoice(db)
    return data


# ------------------------------------------------------------
# POST /billing
# ------------------------------------------------------------
@router.post("", response_model=InvoiceResponse, status_code=201)
@require_role(["admin", "cashier"])
async def route_create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    try:
        invoice = await create_invoice(
            _user,
            db,
            quotation_id=payload.quotation_id,
            sales_order_id=payload.sales_order_id
        )
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------
# GET /billing
# ------------------------------------------------------------
@router.get("", response_model=List[InvoiceResponse])
async def get_all_invoices_route(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    invoices = await get_all_invoices(
        db,
        limit=limit,
        offset=offset,
        status=status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
    )
    return invoices


# ------------------------------------------------------------
# GET /billing/{invoice_id}
# ------------------------------------------------------------
@router.get("/{invoice_id}", response_model=InvoiceResponse)
@require_role(["admin", "cashier"])
async def route_get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    invoice = await get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


# ------------------------------------------------------------
# GET /billing/customer/{customer_id}
# ------------------------------------------------------------
@router.get("/customer/{customer_id}", response_model=List[InvoiceResponse])
@require_role(["admin", "cashier"])
async def route_invoices_by_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    invoices = await get_invoices_by_customer(db, customer_id)
    return invoices


# ------------------------------------------------------------
# POST /billing/{invoice_id}/discount
# ------------------------------------------------------------
@router.post("/{invoice_id}/discount", response_model=InvoiceResponse)
@require_role(["admin", "cashier"])
async def route_apply_discount(
    invoice_id: int,
    payload: DiscountApply,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    try:
        inv = await apply_discount(
            _user,
            db,
            invoice_id,
            payload.discount_amount,
            note=payload.note
        )
        return inv
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------
# POST /billing/{invoice_id}/approve
# ------------------------------------------------------------
@router.post("/{invoice_id}/approve", response_model=ApproveResponse)
@require_role(["admin"])
async def route_approve_invoice(
    invoice_id: int,
    payload: Approve,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    try:
        inv = await approve_invoice(_user, db, invoice_id, payload)
        return {
            "id": inv.id,
            "status": inv.status,
            "approved_by_admin": inv.approved_by_admin
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------
# GET /billing/{invoice_id}/bill
# ------------------------------------------------------------
@router.get("/{invoice_id}/bill")
@require_role(["admin", "cashier"])
async def route_get_bill(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    try:
        bill = await get_final_bill(db, invoice_id)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------------------------------------------------
# POST /billing/payments/{invoice_id}
# ------------------------------------------------------------
@router.post("/payments/{invoice_id}", response_model=PaymentResponse)
@require_role(["admin", "cashier"])
async def route_add_payment(
    invoice_id: int,
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    try:
        payment = await add_payment(
            _user,
            db,
            invoice_id=invoice_id,
            amount=payload.amount,
            payment_method=payload.payment_method
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await award_loyalty_for_invoice(_user, db, invoice_id=invoice_id)
        await log_user_activity(
            db=db,
            user_id=_user.id,
            username=_user.username,
            message=f"Awarded loyalty tokens to Customer for Invoice"
        )
        await db.commit()
    except Exception:
        # Don't block payment success if loyalty fails
        pass

    return payment


# ------------------------------------------------------------
# GET /billing/{invoice_id}/pdf
# ------------------------------------------------------------
@router.get("/{invoice_id}/pdf", response_class=FileResponse)
async def download_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Download invoice PDF."""
    file_path = await generate_invoice_pdf(db, invoice_id)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"Invoice_{invoice_id}.pdf"
    )

# app/routers/billing/quotation_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.quotation_schema import (
    QuotationResponse,
    QuotationListResponse,
    QuotationCreate,
    QuotationUpdate
)
from app.services.billing_services.quotation_service import (
    create_quotation,
    get_quotation,
    list_quotations,
    update_quotation,
    delete_quotation,
    delete_quotation_item,
    get_quotation_list_by_CID,
    approve_quotation,
    move_to_sales,
    move_to_invoice
)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/quotations", tags=["Quotations"])


# --------------------------
# CREATE QUOTATION
# --------------------------
@router.post("/", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
@require_role(["admin", "sales", "cashier"])
async def create_quotation_route(
    data: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await create_quotation(db, data, _user)


# --------------------------
# GET SINGLE QUOTATION BY ID
# --------------------------
@router.get("/{quotation_id}", response_model=QuotationResponse)
@require_role(["admin", "sales", "cashier"])
async def get_quotation_route(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await get_quotation(db, quotation_id)


# --------------------------
# LIST ALL QUOTATIONS
# --------------------------
@router.get("/", response_model=QuotationListResponse)
@require_role(["admin", "sales", "cashier"])
async def list_quotations_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await list_quotations(db)


# --------------------------
# GET QUOTATIONS BY CUSTOMER ID
# --------------------------
@router.get("/customer/{customer_id}", response_model=QuotationListResponse)
@require_role(["admin", "sales", "cashier"])
async def get_quotations_by_customer_route(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await get_quotation_list_by_CID(db, customer_id)


# --------------------------
# UPDATE QUOTATION
# --------------------------
@router.put("/{quotation_id}", response_model=QuotationResponse)
@require_role(["admin", "sales", "cashier"])
async def update_quotation_route(
    quotation_id: int,
    data: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await update_quotation(db, quotation_id, data, _user)


# --------------------------
# DELETE QUOTATION (soft delete)
# --------------------------
@router.delete("/{quotation_id}", response_model=QuotationResponse)
@require_role(["admin"])
async def delete_quotation_route(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await delete_quotation(db, quotation_id, deleted_by=_user.id)


# --------------------------
# APPROVE QUOTATION
# --------------------------
@router.post("/{quotation_id}/approve", response_model=QuotationResponse)
@require_role(["admin"])
async def approve_quotation_route(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await approve_quotation(db, quotation_id, approved_by=_user.id)


# --------------------------
# MOVE QUOTATION TO SALES
# --------------------------
@router.post("/{quotation_id}/move-to-sales", response_model=QuotationResponse)
@require_role(["admin", "sales"])
async def move_quotation_to_sales_route(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await move_to_sales(db, quotation_id, moved_by=_user.id)


# --------------------------
# MOVE QUOTATION TO INVOICE
# --------------------------
@router.post("/{quotation_id}/move-to-invoice", response_model=QuotationResponse)
@require_role(["admin", "sales", "cashier"])
async def move_quotation_to_invoice_route(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await move_to_invoice(db, quotation_id, moved_by=_user.id)


# --------------------------
# DELETE QUOTATION ITEM
# --------------------------
@router.delete("/items/{item_id}", response_model=QuotationResponse)
@require_role(["admin", "sales"])
async def delete_quotation_item_route(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await delete_quotation_item(db, item_id, deleted_by=_user.id)

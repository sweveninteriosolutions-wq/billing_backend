# app/router/stock_transfer_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.stock_transfer_service import (
    create_stock_transfer,
    complete_stock_transfer,
    get_stock_transfer,
    update_stock_transfer,
    delete_stock_transfer,
    get_all_stock_transfers,
    get_stick_transfer_summary_service
)
from app.schemas.stock_transfer_schemas import (
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferOut,
    MessageResponse,
)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])

@router.get("/summary")
@require_role(["admin", "inventory"])
async def get_stick_transfer_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await get_stick_transfer_summary_service(db)

   
# --------------------------
# CREATE STOCK TRANSFER
# --------------------------
@router.post("", response_model=StockTransferOut)
@require_role(["admin", "inventory"])
async def create_transfer_route(
    transfer: StockTransferCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await create_stock_transfer(db, transfer, current_user=_user)


# --------------------------
# COMPLETE STOCK TRANSFER
# --------------------------
@router.post("/{transfer_id}/complete", response_model=StockTransferOut)
@require_role(["admin", "inventory"])
async def complete_transfer_route(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await complete_stock_transfer(db, transfer_id, current_user=_user)


# --------------------------
# GET SINGLE STOCK TRANSFER
# --------------------------
@router.get("/{transfer_id}", response_model=StockTransferOut)
@require_role(["admin", "inventory"])
async def get_transfer_by_id(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await get_stock_transfer(db, transfer_id)


# --------------------------
# GET ALL STOCK TRANSFERS (Paginated + Filtered)
# --------------------------
@router.get("", response_model=list[StockTransferOut])
@require_role(["admin", "inventory"])
async def get_all_transfers(
    status: str = Query(None, description="Filter by status: pending/completed/cancelled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await get_all_stock_transfers(db, status=status, page=page, page_size=page_size)


# --------------------------
# UPDATE STOCK TRANSFER
# --------------------------
@router.put("/{transfer_id}", response_model=StockTransferOut)
@require_role(["admin", "inventory"])
async def update_transfer_route(
    transfer_id: int,
    data: StockTransferUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await update_stock_transfer(db, transfer_id, data, current_user=_user)


# --------------------------
# DELETE STOCK TRANSFER
# --------------------------
@router.delete("/{transfer_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_transfer_route(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await delete_stock_transfer(db, transfer_id, current_user=_user)
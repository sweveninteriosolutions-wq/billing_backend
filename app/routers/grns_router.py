# app/routers/grn_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db import get_db
from app.services.grn_service import (
    create_grn,
    verify_grn,
    get_all_grns,
    delete_grn,
)
from app.schemas.grn_schemas import (
    GRNCreate,
    GRNCreateResponse,
    GRNListResponse,
    MessageResponse,
)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/grns", tags=["GRNs CRUD"])

# -----------------------------------------------------------
# CREATE GRN
# -----------------------------------------------------------
@router.post("", response_model=GRNCreateResponse)
@require_role(["admin", "inventory"])
async def create_grn_route(
    grn: GRNCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await create_grn(db, grn, current_user=_user)


# -----------------------------------------------------------
# VERIFY GRN
# -----------------------------------------------------------
@router.post("/{grn_id}/verify", response_model=GRNCreateResponse)
@require_role(["admin"])
async def verify_grn_route(
    grn_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await verify_grn(db, grn_id, current_user=_user)


# -----------------------------------------------------------
# LIST ALL GRNs (with filters + pagination)
# -----------------------------------------------------------
@router.get("", response_model=GRNListResponse)
@require_role(["admin", "inventory"])
async def list_grns(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by GRN status"),
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    start_date: Optional[str] = Query(None, description="Filter from created_at date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter until created_at date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    return await get_all_grns(db, status, supplier_id, start_date, end_date, page, page_size, sort_by, order)


# -----------------------------------------------------------
# DELETE GRN
# -----------------------------------------------------------
@router.delete("/{grn_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_grn_route(
    grn_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await delete_grn(db, grn_id, current_user=_user)

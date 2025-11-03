from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date
from app.schemas.discount_schemas import DiscountCreate, DiscountUpdate, DiscountOut
from app.services.discount_service import (
    create_discount,
    get_all_discounts,
    get_discount_by_id,
    update_discount,
    delete_discount,
)
from app.utils.check_roles import require_role
from fastapi import Query
from app.core.db import get_db
from app.models.user_models import User
from app.utils.get_user import get_current_user

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.post("/", response_model=DiscountOut)
@require_role(["admin"])
async def route_create_discount(
    payload: DiscountCreate,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Create a new discount (e.g., Summer Sale).
    Performs validations for date range, duplicate code, and value logic.
    """
    return await create_discount(db, payload, _user)




@router.get("/", response_model=List[DiscountOut])
async def route_get_all_discounts(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by status (active/inactive/deleted)"),
    code: str | None = Query(None, description="Filter by discount code (exact or partial)"),
    name: str | None = Query(None, description="Filter by name (partial match)"),
    discount_type: str | None = Query(None, description="Filter by type (percentage/flat)"),
    start_date: date | None = Query(None, description="Filter discounts starting on/after this date"),
    end_date: date | None = Query(None, description="Filter discounts ending on/before this date"),
    include_deleted: bool = Query(False, description="Include soft-deleted discounts"),
):
    """
    Fetch all discounts with optional filters.
    Supports status, code, name, type, and date range filters.
    Example:
    /discounts?status=active&discount_type=percentage
    /discounts?start_date=2025-01-01&end_date=2025-02-01
    """
    return await get_all_discounts(
        db=db,
        status=status,
        code=code,
        name=name,
        discount_type=discount_type,
        start_date=start_date,
        end_date=end_date,
        include_deleted=include_deleted,
    )



@router.get("/{discount_id}", response_model=DiscountOut)
async def route_get_discount(discount_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a single discount by ID."""
    discount = await get_discount_by_id(db, discount_id)
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")
    return discount


@router.put("/{discount_id}", response_model=DiscountOut)
@require_role(["admin"])
async def route_update_discount(
    discount_id: int,
    payload: DiscountUpdate,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Update discount details (status, dates, etc.)."""
    updated = await update_discount(db, discount_id, payload, _user)
    if not updated:
        raise HTTPException(status_code=404, detail="Discount not found")
    return updated


@router.delete("/{discount_id}", response_model=DiscountOut)
@require_role(["admin"])
async def route_delete_discount(
    discount_id: int,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Soft delete a discount — keeps record for audit/history."""
    deleted = await delete_discount(db, discount_id, _user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Discount not found")
    return deleted

@router.patch("/{discount_id}/reactivate", response_model=DiscountOut)
@require_role(["admin"])
async def route_reactivate_discount(
    discount_id: int,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Reactivate a previously soft-deleted discount.
    Restores 'is_deleted' to False and sets status to 'active'.
    """
    from app.services.discount_service import reactivate_discount
    return await reactivate_discount(db, discount_id, _user)

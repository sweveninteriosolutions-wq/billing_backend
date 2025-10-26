# app/routers/auth/activity_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.db import get_db
from app.services.activity_service import get_user_activities
from app.schemas.activity_schemas import UserActivityOut, UserActivityListResponse
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/activities", tags=["User Activities"])

@router.get("/", response_model=UserActivityListResponse)
@require_role(["admin"])
async def list_user_activities(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    user_id: Optional[int] = Query(None),
    username: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc")
):
    """
    Fetch user activity logs with pagination, filtering, and sorting.
    """
    total, activities = await get_user_activities(
        db=db,
        user_id=user_id,
        username=username,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order
    )

    return UserActivityListResponse(
        message="User activities fetched successfully",
        total=total,
        data=[UserActivityOut.model_validate(a) for a in activities]
    )

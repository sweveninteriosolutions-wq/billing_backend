# app/services/activity_services.py
from sqlalchemy import select, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import List, Optional, Tuple
from app.models.activity_models import UserActivity

ALLOWED_SORT_FIELDS = {"id", "user_id", "username", "created_at"}

async def get_user_activities(
    db: AsyncSession,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc"
) -> Tuple[int, List[UserActivity]]:
    try:
        # Validate sort field
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "created_at"

        sort_column = getattr(UserActivity, sort_by)
        sort_order = desc(sort_column) if order.lower() == "desc" else asc(sort_column)

        # Build filters
        filters = []
        if user_id:
            filters.append(UserActivity.user_id == user_id)
        if username:
            filters.append(UserActivity.username.ilike(f"%{username}%"))

        # Base query
        stmt = select(UserActivity)
        count_stmt = select(func.count(UserActivity.id))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        # Count total
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Pagination + sorting
        stmt = stmt.order_by(sort_order).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        activities = result.scalars().all()

        return total, activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activities: {e}")

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, asc, func
from fastapi import HTTPException
from app.models.activity_models import UserActivity
from typing import List, Optional, Tuple

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
    """
    Fetch paginated user activity with optional filters and sorting.
    Returns total count and list of activities.
    """
    try:
        # Validate sort field
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "created_at"

        sort_order = desc(sort_by) if order.lower() == "desc" else asc(sort_by)

        # Build base query
        stmt = select(UserActivity)
        count_stmt = select(func.count(UserActivity.id))

        if user_id:
            stmt = stmt.where(UserActivity.user_id == user_id)
            count_stmt = count_stmt.where(UserActivity.user_id == user_id)
        if username:
            stmt = stmt.where(UserActivity.username.ilike(f"%{username}%"))
            count_stmt = count_stmt.where(UserActivity.username.ilike(f"%{username}%"))

        # Get total count
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply sorting + pagination
        stmt = stmt.order_by(sort_order).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        activities = result.scalars().all()

        return total, activities

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activities: {str(e)}")

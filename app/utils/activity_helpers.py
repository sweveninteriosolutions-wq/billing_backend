# app/utils/activity_helpers.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_models import UserActivity

async def log_user_activity(db: AsyncSession, user_id: int = None, username: str = None, message: str = "", commit: bool = False):
    """
    Adds a user activity log to the session. The caller is responsible for the commit.
    """
    activity = UserActivity(
        user_id=user_id,
        username=username,
        message=message
    )
    db.add(activity)
    if commit:
        await db.commit()
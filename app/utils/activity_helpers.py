# app/utils/activity_helpers.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_models import UserActivity

async def log_user_activity(db: AsyncSession, user_id: int = None, username: str = None, message: str = ""):
    """
    Log a simple human-readable activity message to the database.
    """
    activity = UserActivity(
        user_id=user_id,
        username=username,
        message=message
    )
    db.add(activity)
    await db.commit()

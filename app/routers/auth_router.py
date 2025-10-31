from fastapi import APIRouter, Depends, HTTPException, Body, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy.sql import func

from app.core.db import get_db
from app.schemas.auth_schemas import UserLogin, TokenResponse, MessageResponse
from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    refresh_access_token,
    logout_user,
)
from app.utils.get_user import get_current_user
from app.utils.activity_helpers import log_user_activity
from app.services.alerts_service import get_stock_alerts
from app.models.user_models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


# --------------------------
# LOGIN
# --------------------------
@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue access + refresh tokens."""
    user = await authenticate_user(db, data.username, data.password)

    # Update last_login + mark online
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=func.now(), is_online=True)
    )

    access_token, refresh_token = await create_tokens(db, user)

    # Log login activity
    await log_user_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        message=f"User '{user.username}' logged in.",
    )

    # Optional: Auto stock alert check for admin/inventory
    if user.role in ["admin", "inventory"]:
        try:
            alerts = await get_stock_alerts(db, current_user=user)
            alert_count = len(alerts)
            await log_user_activity(
                db=db,
                user_id=user.id,
                username=user.username,
                message=f"Auto stock check done on login ({alert_count} items below threshold).",
            )
        except Exception as e:
            print(f"Stock alert auto-check failed: {e}")

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
    )


# --------------------------
# REFRESH TOKEN
# --------------------------
@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token_endpoint(
    request: Request,
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and return new token pair."""
    new_token_data = await refresh_access_token(db, refresh_token)

    await log_user_activity(
        db=db,
        user_id=new_token_data.get("user_id"),
        username=new_token_data.get("username"),
        message="User refreshed access token.",
    )
    await db.commit()

    return TokenResponse(
        access_token=new_token_data["access_token"],
        refresh_token=new_token_data["refresh_token"],
        token_type="bearer",
    )


# --------------------------
# LOGOUT
# --------------------------
@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Logout user, revoke tokens, and mark as offline."""
    response = await logout_user(db, current_user.username)

    # Mark user offline
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(is_online=False)
    )

    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"User '{current_user.username}' logged out.",
    )

    await db.commit()
    return response

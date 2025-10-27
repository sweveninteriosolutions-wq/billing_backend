# File: app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, Body, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue access + refresh tokens."""
    user = await authenticate_user(db, data.username, data.password)

    access_token, refresh_token = await create_tokens(db, user)

    await log_user_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        message=f"User '{user.username}' logged in.",
    )
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
    )


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


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Logout user and revoke active tokens."""
    response = await logout_user(db, current_user.username)

    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"User '{current_user.username}' logged out.",
    )
    await db.commit()

    return response

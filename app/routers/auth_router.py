# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.schemas.user_schemas import UserLogin, TokenResponse, MessageResponse
from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    refresh_access_token,
    logout_user,
)
from app.utils.get_user import get_current_user
from app.utils.activity_helpers import log_user_activity  # ✅ Import activity logger

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, data.username, data.password)
    access_token, refresh_token = await create_tokens(user, db)

    # ✅ Log user login activity
    await log_user_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        message=f"User '{user.username}' logged in successfully."
    )
    await db.commit() 

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    request: Request,
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange a refresh token for a new access token.
    """
    new_token_data = await refresh_access_token(db, refresh_token)

    # ✅ Log token refresh activity
    await log_user_activity(
        db=db,
        user_id=new_token_data.get("user_id"),
        username=new_token_data.get("username"),
        message="User refreshed access token using refresh token."
    )
    await db.commit() 

    return TokenResponse(**new_token_data)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Logs out the user by invalidating their refresh token.
    """
    response = await logout_user(db, current_user.username)

    # ✅ Log logout activity
    await log_user_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"User '{current_user.username}' logged out successfully."
    )
    await db.commit() 

    return response

# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.schemas.user_schemas import UserLogin, TokenResponse
from app.services.auth_service import authenticate_user, create_tokens, refresh_access_token, logout_user
from app.schemas.user_schemas import MessageResponse
from app.utils.get_user import get_current_user 

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.username, data.password)
    access_token, refresh_token = await create_tokens(user, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    Exchange a refresh token for a new access token.
    """
    access_token = await refresh_access_token(db, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/logout", response_model=MessageResponse)
async def logout(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Logs out the user by invalidating their refresh token.
    """
    return await logout_user(db, current_user.username)
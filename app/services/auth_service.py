# app/services/auth_service.py
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError
from app.models.user_models import User
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET,
    JWT_ALGORITHM
)

async def authenticate_user(db: AsyncSession, username: str, password: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user

async def create_tokens(user: User, db: AsyncSession):
    """
    Create access and refresh tokens for all users.
    Stores the refresh token in the database.
    """
    # Access token
    expire_minutes = ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES if user.role == "admin" else ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        {"sub": user.username, "role": user.role},
        timedelta(minutes=expire_minutes)
    )

    # Refresh token for all users
    refresh_token = create_refresh_token(
        {"sub": user.username, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    user.refresh_token = refresh_token
    await db.commit()

    return access_token, refresh_token

async def refresh_access_token(db: AsyncSession, refresh_token: str):
    """
    Exchange a refresh token for a new access token.
    """
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or user.refresh_token != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token mismatch")

    # Create new access token
    expire_minutes = ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES if user.role == "admin" else ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token({"sub": user.username, "role": user.role}, timedelta(minutes=expire_minutes))

    return access_token

async def logout_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Invalidate refresh token
    user.refresh_token = None
    await db.commit()
    return {"msg": "Logged out successfully"}

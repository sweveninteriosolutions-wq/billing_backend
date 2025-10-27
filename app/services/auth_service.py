# app/services/auth_service.py
from datetime import timedelta
from typing import Dict
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models.user_models import User, RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES,
)


async def authenticate_user(db: AsyncSession, username: str, password: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return user


async def create_tokens(db: AsyncSession, user: User):
    """
    Create new access and refresh tokens.
    Includes token_version to support immediate logout invalidation.
    """
    expire_minutes = (
        ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES
        if user.role == "admin"
        else ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = create_access_token(
        {"sub": user.username, "user_id": user.id, "role": user.role},
        token_version=user.token_version,
        expires_delta=timedelta(minutes=expire_minutes),
    )

    refresh_token = create_refresh_token(
        {"sub": user.username, "type": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    user.refresh_token = refresh_token
    await db.commit()
    await db.refresh(user)

    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, old_refresh_token: str) -> Dict:
    """
    Rotate refresh token: must find the DB record and ensure it is not revoked.
    Marks old token revoked and issues a new refresh token record.
    """
    try:
        payload = decode_token(old_refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    username = payload.get("sub")
    user_id = payload.get("user_id")

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == old_refresh_token)
    )
    db_token = result.scalars().first()

    if not db_token or db_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or reused refresh token",
        )

    db_token.revoked = True
    await db.flush()

    new_access_token = create_access_token(
        {"sub": username, "user_id": user_id, "role": db_token.user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    new_refresh_token_str = create_refresh_token(
        {"sub": username, "user_id": user_id}
    )

    new_refresh_record = RefreshToken(user_id=user_id, token=new_refresh_token_str)
    db.add(new_refresh_record)
    await db.flush()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token_str,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
    }


async def logout_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.token_version += 1

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(revoked=True)
    )

    await db.flush()

    return {"msg": "Logged out successfully"}

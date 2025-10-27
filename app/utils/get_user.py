# app/utils/get_user.py
from fastapi import Depends, HTTPException, status, Header
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.requests import Request

from app.models.user_models import User
from app.core.db import get_db
from app.core.config import JWT_SECRET, JWT_ALGORITHM


async def get_current_user(
    request: Request,
    token: str = Header(..., description="Access token in Authorization header"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts and validates the current user from the given JWT token.
    Enforces token_version validation for real-time logout invalidation.
    """

    # Decode and verify JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        token_version: int = payload.get("token_version")

        if username is None or token_version is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Retrieve user from DB
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Check if token has been invalidated by version mismatch
    if user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalidated. Please log in again.",
        )

    # Check active status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # Attach user to request context for use in endpoints
    request.state.user = user
    return user

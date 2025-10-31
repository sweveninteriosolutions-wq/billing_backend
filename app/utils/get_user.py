# app/utils/get_user.py
from fastapi import Depends, HTTPException, status, Header
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.requests import Request

from app.models.user_models import User
from app.core.db import get_db
from app.core.config import JWT_SECRET, JWT_ALGORITHM


from fastapi import Request, Depends, HTTPException, status, Header

async def get_current_user(
    request: Request,
    token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Support either header
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ")[1]

    if not raw_token:
        raise HTTPException(status_code=401, detail="Missing access token")

    # Decode token normally
    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        token_version = payload.get("token_version")
        if not username or token_version is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.token_version != token_version:
        raise HTTPException(status_code=401, detail="Token invalidated. Please log in again.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")

    request.state.user = user
    return user

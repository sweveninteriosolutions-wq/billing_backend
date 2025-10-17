# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.user_models import User
from app.core.security import hash_password
from app.schemas.user_schemas import UserCreate, UserUpdate

# Define allowed roles
ALLOWED_ROLES = {"admin", "cashier", "sales", "inventory"}  # add all valid roles here

# ---------------------------
# CREATE USER
# ---------------------------
async def create_user(db: AsyncSession, user_data: UserCreate):
    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == user_data.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Validate role
    if user_data.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")

    # Validate password length
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ---------------------------
# LIST ALL USERS
# ---------------------------
async def list_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


# ---------------------------
# GET USER BY ID
# ---------------------------
async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------
# UPDATE USER
# ---------------------------
async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate):
    target_user = await get_user_by_id(db, user_id)

    # Update username with uniqueness check
    if user_data.username:
        existing_user_check = await db.execute(
            select(User).where(User.username == user_data.username, User.id != user_id)
        )
        if existing_user_check.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        target_user.username = user_data.username

    # Update password with length validation
    if user_data.password:
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        target_user.password_hash = hash_password(user_data.password)

    # Update role with validation
    if user_data.role:
        if user_data.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")
        target_user.role = user_data.role

    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)
    return target_user


# ---------------------------
# DELETE USER
# ---------------------------
async def delete_user(db: AsyncSession, user_id: int):
    target_user = await get_user_by_id(db, user_id)
    await db.delete(target_user)
    await db.commit()
    return target_user

# app/services/user_services.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status
from app.models.user_models import User
from app.core.security import hash_password
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.utils.activity_helpers import log_user_activity

ALLOWED_ROLES = {"admin", "cashier", "sales", "inventory"}


# CREATE USER
async def create_user(db: AsyncSession, user_data: UserCreate, current_user):
    existing = await db.execute(select(User).where(User.username == user_data.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if user_data.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")

    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    await db.flush()

    if current_user:
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} created user '{new_user.username}' with role {new_user.role}"
        )

    await db.commit()
    await db.refresh(new_user)
    return new_user


# LIST USERS
async def list_users(
    db: AsyncSession,
    role: str | None = None,
    is_active: bool | None = None,
    limit: int = 20,
    offset: int = 0
):
    """
    Return paginated, filtered list of users.
    Supports filtering by role and active/inactive status.
    """
    query = select(User)

    filters = []
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# GET USER BY ID
async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# UPDATE USER
async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate, current_user):
    user = await get_user_by_id(db, user_id)
    changes = []

    if user_data.username and user_data.username != user.username:
        existing_check = await db.execute(select(User).where(User.username == user_data.username, User.id != user_id))
        if existing_check.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        old_username = user.username 
        user.username = user_data.username
        changes.append(f"username changed to '{user_data.username}'")

    if user_data.password:
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.password_hash = hash_password(user_data.password)
        changes.append("password updated")

    if user_data.role and user_data.role != user.role:
        if user_data.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")
        user.role = user_data.role
        changes.append(f"role changed to '{user_data.role}'")

    if current_user and changes:
        change_summary = ", ".join(changes)
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} updated {old_username}: {change_summary}"
        )

    await db.commit()
    await db.refresh(user)
    return user


# DELETE USER (soft delete)
async def delete_user(db: AsyncSession, user_id: int, current_user):
    user = await get_user_by_id(db, user_id)
    user.is_active = False

    if current_user:
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} deactivated user '{user.username}'"
        )

    await db.commit()
    return user

# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.user_models import User
from app.core.security import hash_password
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.utils.activity_helpers import log_user_activity

# ---------------------------
# Allowed roles
# ---------------------------
ALLOWED_ROLES = {"admin", "cashier", "sales", "inventory"}  # Add all valid roles here


# ---------------------------
# CREATE USER
# ---------------------------
async def create_user(db: AsyncSession, user_data: UserCreate, current_user):
    """
    Create a new user and log the activity in a single transaction.
    """
    try:
        # 1️⃣ Check username uniqueness
        existing = await db.execute(select(User).where(User.username == user_data.username))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # 2️⃣ Validate role
        if user_data.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")

        # 3️⃣ Validate password length
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        # 4️⃣ Create user (not committed yet)
        new_user = User(
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            role=user_data.role
        )
        db.add(new_user)
        await db.flush()  # ensures new_user.id is available

        # 5️⃣ Log activity (same transaction)
        if current_user:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=(
                    f"{current_user.role.capitalize()} created {new_user.role} "
                    f"with username {new_user.username} and user id {new_user.id}"
                )
            )

        # 6️⃣ Commit once — both user + activity are persisted atomically
        await db.commit()
        await db.refresh(new_user)
        return new_user

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")


# ---------------------------
# LIST ALL USERS
# ---------------------------
async def list_users(db: AsyncSession):
    """
    Return all users.
    """
    result = await db.execute(select(User))
    return result.scalars().all()


# ---------------------------
# GET USER BY ID
# ---------------------------
async def get_user_by_id(db: AsyncSession, user_id: int):
    """
    Fetch a single user by ID.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------
# UPDATE USER
# ---------------------------
# ---------------------------
# UPDATE USER
# ---------------------------
async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate, current_user):
    """
    Update a user and log a descriptive message.
    """
    target_user = await get_user_by_id(db, user_id)
    changes = []

    # Update username
    if user_data.username:
        existing_user_check = await db.execute(
            select(User).where(User.username == user_data.username, User.id != user_id)
        )
        if existing_user_check.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        changes.append(f"username to {user_data.username}")
        target_user.username = user_data.username

    # Update password
    if user_data.password:
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        target_user.password_hash = hash_password(user_data.password)
        changes.append("password")

    # Update role
    if user_data.role:
        if user_data.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Role must be one of {ALLOWED_ROLES}")
        changes.append(f"role to {user_data.role}")
        target_user.role = user_data.role

    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)

    # Log activity
    if current_user and changes:
        change_summary = ", ".join(changes)
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} updated {target_user.role} "
                    f"with username {target_user.username}: {change_summary}"
        )
        await db.commit()  # ✅ commit the log

    return target_user



# ---------------------------
# DELETE USER
# ---------------------------
# ---------------------------
# DELETE USER
# ---------------------------
async def delete_user(db: AsyncSession, user_id: int, current_user):
    """
    Soft-delete (deactivate) a user and log a descriptive message.
    """
    target_user = await get_user_by_id(db, user_id)
    target_user.is_active = False
    db.add(target_user)
    await db.commit()

    # Log activity
    if current_user:
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} deactivated {target_user.role} "
                    f"with username {target_user.username}"
        )
        await db.commit()  # ✅ commit the log

    return target_user
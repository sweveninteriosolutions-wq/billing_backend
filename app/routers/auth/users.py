# app/routers/users_routes.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.schemas.user_schemas import (
    UserCreate, UserUpdate, UserResponse, UsersListResponse, MessageResponse
)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role
from app.services.user_service import (
    create_user, list_users, get_user_by_id, update_user,
    delete_user
)

router = APIRouter(prefix="/users", tags=["Users CRUD"])

# ---------------------------
# CREATE USER
# ---------------------------
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@require_role(["admin"])
async def create_user_route(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user)
):
    new_user = await create_user(db, user_data)
    return {"msg": f"User '{new_user.username}' created successfully.", "data": new_user}


# ---------------------------
# LIST ALL USERS
# ---------------------------
@router.get("/", response_model=UsersListResponse)
@require_role(["admin"])
async def list_users_route(db: AsyncSession = Depends(get_db), _user = Depends(get_current_user)):
    users = await list_users(db)
    return {"msg": f"{len(users)} users fetched successfully.", "data": users}


# ---------------------------
# GET SINGLE USER
# ---------------------------
@router.get("/{user_id}", response_model=UserResponse)
@require_role(["admin"])
async def get_user_route(user_id: int, db: AsyncSession = Depends(get_db), _user = Depends(get_current_user)):
    target_user = await get_user_by_id(db, user_id)
    return {"msg": f"User with ID {user_id} fetched successfully.", "data": target_user}


# ---------------------------
# UPDATE USER
# ---------------------------
@router.put("/{user_id}", response_model=UserResponse)
@require_role(["admin"])
async def update_user_route(user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db), _user = Depends(get_current_user)):
    updated_user = await update_user(db, user_id, user_data)
    return {"msg": f"User '{updated_user.username}' updated successfully.", "data": updated_user}


# ---------------------------
# DELETE USER
# ---------------------------
@router.delete("/{user_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_user_route(user_id: int, db: AsyncSession = Depends(get_db), _user = Depends(get_current_user)):
    deleted_user = await delete_user(db, user_id)
    return {"msg": f"User '{deleted_user.username}' deleted successfully."}

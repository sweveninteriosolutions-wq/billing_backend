# app/schemas/user_schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserOut(UserBase):
    id: int
    is_active:bool
    last_login: Optional[datetime] = None
    is_online:bool

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    msg: str

# ✅ Unified structure for all endpoints
class UserResponse(BaseModel):
    msg: str
    data: Optional[UserOut] = None

class UsersListResponse(BaseModel):
    msg: str
    data: List[UserOut]

# File: app/schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from typing import Literal

class UserLogin(BaseModel):
    username: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: Literal["bearer"] = "bearer"

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: EmailStr
    role: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    msg: str

class UsersListResponse(BaseModel):
    msg: str
    data: List[UserOut]

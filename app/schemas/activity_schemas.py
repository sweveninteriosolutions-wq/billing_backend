# app/schemas/activity_schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserActivityOut(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserActivityListResponse(BaseModel):
    message: str
    total: int
    data: List[UserActivityOut]

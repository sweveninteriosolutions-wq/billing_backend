from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime

class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None

class CustomerOut(CustomerBase):
    id: int
    is_active: bool
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_by_name: Optional[str] = None  # NEW
    updated_by_name: Optional[str] = None  # NEW
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerResponse(BaseModel):
    message: str
    data: Optional[CustomerOut] = None

class CustomerListResponse(BaseModel):
    message: str
    total: int
    data: List[CustomerOut]
    warning: Optional[str] = None  # NEW: warning message for invalid sort_by


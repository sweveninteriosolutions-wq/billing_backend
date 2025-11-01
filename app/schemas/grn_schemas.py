# app/schemas/grn_schemas.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --------------------------
# GRN Schemas
# --------------------------
class GRNItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float

class GRNCreate(BaseModel):
    supplier_id: int
    purchase_order: Optional[str]
    notes: Optional[str]
    bill_number: Optional[str]
    bill_file: Optional[str] = None  # path or filename
    items: List[GRNItemCreate]

class GRNItemOut(GRNItemCreate):
    id: int
    total: float

    class Config:
        from_attributes = True

class GRNOut(BaseModel):
    id: int
    supplier_id: int
    purchase_order: Optional[str]
    sub_total: float
    total_amount: float
    notes: Optional[str]
    bill_number: Optional[str]
    bill_file: Optional[str]
    created_by: int
    verified_by: Optional[int]
    status: str
    created_at: datetime
    items: List[GRNItemOut]

    class Config:
        from_attributes = True

class GRNCreateResponse(BaseModel):
    message: str
    data: GRNOut

class GRNListResponse(BaseModel):
    message: str
    data: List[GRNOut]

# --------------------------
# Generic Message Response
# --------------------------
class MessageResponse(BaseModel):
    message: str
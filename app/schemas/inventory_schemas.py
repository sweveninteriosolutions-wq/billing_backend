from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from pydantic import field_validator
from app.models.product_models import LocationEnum


# --------------------------
# Product Schemas
# --------------------------
class ProductBase(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity_showroom: Optional[int] = None
    quantity_warehouse: Optional[int] = None
    min_stock_threshold: Optional[int] = None

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    quantity_showroom: int
    quantity_warehouse: int
    min_stock_threshold: int

    @field_validator('price', 'quantity_showroom', 'quantity_warehouse', 'min_stock_threshold')
    def non_negative_values(cls, value):
        if value < 0:
            raise ValueError('Must be non-negative')
        return value

class ProductUpdate(ProductBase):
    """All fields optional for partial updates."""
    pass

class ProductOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    price: float
    quantity_showroom: int
    quantity_warehouse: int
    min_stock_threshold: int
    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    message: str
    data: Optional[ProductOut] = None

class ProductListResponse(BaseModel):
    message: str
    data: List[ProductOut]


# --------------------------
# Stock Alert Schema
# --------------------------
class StockAlert(BaseModel):
    product_id: int
    product_name: str
    quantity_showroom: int
    quantity_total: int
    min_stock_threshold: int


# --------------------------
# Supplier Schemas
# --------------------------
class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None

class SupplierOut(SupplierCreate):
    id: int

    class Config:
        from_attributes = True

class SupplierListResponse(BaseModel):
    message: str
    data: List[SupplierOut]

class SupplierCreateResponse(BaseModel):
    message: str
    data: SupplierOut


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
    bill_file: Optional[str]  # path or filename
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
# Stock Transfer Schemas
# --------------------------
class TransferCreate(BaseModel):
    product_id: int
    quantity: int
    from_location: LocationEnum
    to_location: LocationEnum

class TransferOut(TransferCreate):
    id: int
    status: str
    transferred_by: int
    completed_by: Optional[int]
    transfer_date: datetime

    class Config:
        from_attributes = True

class TransferResponse(BaseModel):
    message: str
    data: TransferOut

class TransferListResponse(BaseModel):
    message: str
    data: List[TransferOut]

class TransferUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    from_location: Optional[LocationEnum] = None
    to_location: Optional[LocationEnum] = None


# --------------------------
# Generic Message Response
# --------------------------
class MessageResponse(BaseModel):
    message: str

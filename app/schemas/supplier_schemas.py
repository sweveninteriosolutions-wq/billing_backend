# app/schemas/supplier_schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# -----------------------------
# Supplier Schemas
# -----------------------------
class SupplierCreate(BaseModel):
    """Schema for creating a new supplier"""
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class SupplierUpdate(BaseModel):
    """Schema for updating an existing supplier"""
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class SupplierOut(SupplierCreate):
    """Schema for returning supplier data"""
    id: int

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    """Schema for returning a list of suppliers"""
    message: str
    total: int
    data: List[SupplierOut]


class SupplierCreateResponse(BaseModel):
    """Schema for returning a newly created supplier"""
    message: str
    data: SupplierOut


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# -----------------------------
# GRN Schemas
# -----------------------------
class GRNResponse(BaseModel):
    """Schema for a single GRN record"""
    id: int
    grn_number: str
    supplier_id: int
    status: str
    total_amount: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class GRNResponseList(BaseModel):
    """Schema for returning multiple GRN records"""
    message: str
    total: int
    data: List[GRNResponse]


# -----------------------------
# Product Schemas
# -----------------------------
class ProductOut(BaseModel):
    """Schema for a single product record"""
    id: int
    name: str
    sku: Optional[str] = None
    supplier_id: Optional[int] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for returning multiple product records"""
    message: str
    total: int
    data: List[ProductOut]

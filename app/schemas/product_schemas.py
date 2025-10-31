# app/schemas/product_schemas.py

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from app.models.product_models import LocationEnum

# --------------------------
# Base schema for Product
# --------------------------
class ProductBase(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity_showroom: Optional[int] = None
    quantity_warehouse: Optional[int] = None
    min_stock_threshold: Optional[int] = None


# --------------------------
# Schema for creating Product
# --------------------------
class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    quantity_showroom: int
    quantity_warehouse: int
    min_stock_threshold: int
    supplier_id: int

    @field_validator('price', 'quantity_showroom', 'quantity_warehouse', 'min_stock_threshold')
    def non_negative_values(cls, value):
        """
        Ensure numeric fields are non-negative.
        """
        if value < 0:
            raise ValueError('Must be non-negative')
        return value


# --------------------------
# Schema for updating Product
# --------------------------
class ProductUpdate(ProductBase):
    """
    All fields optional for partial updates.
    """
    pass


# --------------------------
# Output schema for single Product
# --------------------------
class ProductOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    price: float
    quantity_showroom: int
    quantity_warehouse: int
    min_stock_threshold: int
    supplier_id : Optional[int]= None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --------------------------
# Response schemas
# --------------------------
class ProductResponse(BaseModel):
    message: str
    data: Optional[ProductOut] = None


class ProductListResponse(BaseModel):
    message: str
    data: List[ProductOut]


# --------------------------
# Generic Message Response
# --------------------------
class MessageResponse(BaseModel):
    message: str

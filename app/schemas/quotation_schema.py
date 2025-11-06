# app/schemas/quotation_schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal

# --------------------------
# Quotation Item Schemas
# --------------------------
class QuotationItemCreate(BaseModel):
    product_id: int
    quantity: int

class QuotationItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    total: Decimal

    class Config:
        from_attributes = True

class QuotationItemUpdate(BaseModel):
    id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    is_deleted: Optional[bool] = None

# --------------------------
# Quotation Schemas
# --------------------------
class QuotationCreate(BaseModel):
    customer_id: int                     # Mandatory
    items: List[QuotationItemCreate]     # Mandatory
    notes: Optional[str] = None          # Optional
    description: Optional[str] = None    # Optional
    additional_data: Optional[Dict] = None  # Optional, more explicit than dict

class QuotationUpdate(BaseModel):
    customer_id: Optional[int] = None          # allows reassigning to another customer
    notes: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[QuotationItemUpdate]] = None  # allow updating quantities or products
    approved: Optional[bool] = None
    moved_to_sales: Optional[bool] = None
    moved_to_invoice: Optional[bool] = None
    is_deleted: Optional[bool] = None

class QuotationOut(BaseModel):
    id: int
    quotation_number: str
    customer_id: int
    description: Optional[str]
    notes: Optional[str]
    total_items_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    additional_data: Optional[Dict] = None
    approved: bool
    moved_to_sales: bool
    moved_to_invoice: bool
    issue_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    items: List[QuotationItemOut] = []

    class Config:
        from_attributes = True

# --------------------------
# Response Schemas
# --------------------------
class QuotationResponse(BaseModel):
    message: Optional[str] = None
    data: Optional[QuotationOut] = None

class QuotationListResponse(BaseModel):
    message: str
    data: List[QuotationOut] = []

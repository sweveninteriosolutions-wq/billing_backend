from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


# =====================================================
# 🔹 Nested / Helper Schemas
# =====================================================
class CompletionStatusStep(BaseModel):
    date: str
    status: str
    note: Optional[str] = None

    model_config = {"from_attributes": True}


class SalesOrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

    model_config = {"from_attributes": True}


class QuotationInfo(BaseModel):
    id: int
    quotation_number: str
    description: Optional[str]

    model_config = {"from_attributes": True}


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    address: Optional[dict]

    model_config = {"from_attributes": True}


class QuotationItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str]
    quantity: int
    unit_price: Decimal
    total: Decimal

    model_config = {"from_attributes": True}


class QuotationDetailResponse(BaseModel):
    id: int
    quotation_number: str
    description: Optional[str]
    notes: Optional[str]
    total_items_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    approved: bool
    moved_to_sales: bool
    created_at: datetime
    updated_at: Optional[datetime]
    customer: CustomerResponse
    items: List[QuotationItemResponse] = []

    model_config = {"from_attributes": True}


class QuotationDetailMessageResponse(BaseModel):
    message: str
    Data: Optional[List[QuotationDetailResponse]] = None


class QuotationStatusResponse(BaseModel):
    id: int
    quotation_number: str
    customer_id: int
    approved: bool
    moved_to_sales: bool
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# =====================================================
# 🔹 Sales Order Listing Schemas
# =====================================================
class SalesOrderListResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    approved: bool
    moved_to_invoice: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SalesOrderListMessage(BaseModel):
    message: str
    Data: Optional[List[SalesOrderListResponse]] = None


# =====================================================
# 🔹 Main Sales Order Response Schemas
# =====================================================
class SalesOrderResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    quotation_id: int
    quotation: Optional[QuotationInfo] = None
    quotation_items: List[SalesOrderItemResponse]
    completion_status: List[CompletionStatusStep]
    completion_flag: bool
    approved: bool
    moved_to_invoice: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SalesOrderMessageResponse(BaseModel):
    message: str
    Data: Optional[SalesOrderResponse] = None


# =====================================================
# 🔹 Message Schema
# =====================================================
class SalesOrderMessage(BaseModel):
    message: str
    date: datetime = datetime.utcnow()


# =====================================================
# 🔹 Input / Request Schemas
# =====================================================
class SalesOrderCreate(BaseModel):
    quotation_id: int


class SalesOrderStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

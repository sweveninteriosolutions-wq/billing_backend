from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List, Any
from datetime import datetime
from typing_extensions import Annotated
from app.models.invoice_models import InvoiceStatus

from app.schemas.customer_schema import CustomerOut
from app.schemas.sales_order_schema import SalesOrderResponse
from app.schemas.quotation_schema import QuotationOut
from app.schemas.discount_schemas import DiscountOut

# -------------------------------------------------------------------------
# Define reusable constrained Decimal types
# -------------------------------------------------------------------------
PositiveDecimal = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


# -------------------------------------------------------------------------
# Payment Schemas
# -------------------------------------------------------------------------
class PaymentCreate(BaseModel):
    amount: PositiveDecimal
    payment_method: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    customer_id: int
    amount: Decimal
    payment_method: Optional[str]
    payment_date: datetime

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}


# -------------------------------------------------------------------------
# Invoice Schemas
# -------------------------------------------------------------------------
class InvoiceCreate(BaseModel):
    quotation_id: Optional[int] = None
    sales_order_id: Optional[int] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_id: int
    quotation_id: Optional[int]
    sales_order_id: Optional[int]
    total_amount: Decimal
    discounted_amount: Decimal
    total_paid: Decimal
    balance_due: Decimal
    status: InvoiceStatus
    approved_by_admin: bool
    loyalty_claimed: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}


class InvoiceDetailedResponse(BaseModel):
    id: int
    invoice_number: str
    customer: Optional[CustomerOut] = None
    quotation: Optional[QuotationOut] = None
    sales_order: Optional[SalesOrderResponse] = None
    discount: Optional[DiscountOut] = None
    total_amount: Decimal
    discounted_amount: Decimal
    total_paid: Decimal
    balance_due: Decimal
    status: InvoiceStatus
    approved_by_admin: bool
    loyalty_claimed: bool
    created_at: datetime
    updated_at: Optional[datetime]
    payments: List[PaymentResponse] = []

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}


# -------------------------------------------------------------------------
# Discount & Approval Schemas
# -------------------------------------------------------------------------
class DiscountApply(BaseModel):
    code: str = Field(..., description="Discount code to apply (e.g. DR-005)")
    note: Optional[str] = None


class Approve(BaseModel):
    discount_amount: Optional[NonNegativeDecimal] = None
    note: Optional[str] = None

    class Config:
        orm_mode = True


class ApproveResponse(BaseModel):
    id: int
    status: InvoiceStatus
    approved_by_admin: bool

    class Config:
        orm_mode = True


# -------------------------------------------------------------------------
# Ready to Invoice Schemas (Enhanced)
# -------------------------------------------------------------------------
class ReadyCustomerResponse(BaseModel):
    """Lightweight Customer structure for ready-to-invoice context."""
    id: Optional[int]
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]


class ReadyQuotationItemResponse(BaseModel):
    """Items within quotation when ready to invoice."""
    id: int
    product_id: int
    product_name: Optional[str]
    quantity: int
    unit_price: str
    total: str


class ReadyQuotationResponse(BaseModel):
    """Quotation details shown in ready-to-invoice response."""
    id: int
    quotation_number: str
    customer_id: int
    customer: Optional[ReadyCustomerResponse]
    total_items_amount: str
    gst_amount: str
    total_amount: str
    items: List[ReadyQuotationItemResponse]


class ReadyQuotationSummary(BaseModel):
    """Nested summary inside sales order for linked quotation."""
    id: Optional[int]
    quotation_number: Optional[str]
    quotation_date: Optional[datetime]


class ReadyQuotationSnapshotItem(BaseModel):
    """Individual snapshot items from quotation in a sales order."""
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class ReadySalesOrderResponse(BaseModel):
    """Sales Order details ready for invoicing."""
    id: int
    sales_order_number: Optional[int]
    customer_id: int
    customer: Optional[ReadyCustomerResponse]
    quotation_id: Optional[int]
    quotation: Optional[ReadyQuotationSummary]
    quotation_snapshot: Optional[List[ReadyQuotationSnapshotItem]]
    total_amount: str
    customer_name: Optional[str]


class ReadyToInvoiceResponse(BaseModel):
    """Final API response structure for ready-to-invoice listing."""
    quotations: List[ReadyQuotationResponse]
    sales_orders: List[ReadySalesOrderResponse]


# -------------------------------------------------------------------------
# Loyalty Schemas
# -------------------------------------------------------------------------
class LoyaltyTokenResponse(BaseModel):
    id: int
    customer_id: int
    invoice_id: int
    tokens: int

    class Config:
        orm_mode = True


class LoyaltySummaryResponse(BaseModel):
    total_tokens: int
    total_transactions: int
    tokens: List[LoyaltyTokenResponse]

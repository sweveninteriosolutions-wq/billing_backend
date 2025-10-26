from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from typing_extensions import Annotated
from app.models.billing_models.invoice_models import InvoiceStatus

# Define reusable constrained Decimal types
PositiveDecimal = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]

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

class DiscountApply(BaseModel):
    discount_amount: NonNegativeDecimal
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

# app/schemas/billing_schemas/invoice_schema.py
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class QuotationItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str]
    quantity: int
    unit_price: Decimal
    total: Decimal

class QuotationReadyResponse(BaseModel):
    id: int
    quotation_number: str
    customer_id: int
    total_amount: Decimal
    gst_amount: Decimal
    total_items_amount: Decimal
    items: List[QuotationItemResponse]

class SalesOrderReadyResponse(BaseModel):
    id: int
    customer_id: int
    quotation_id: int
    quotation_snapshot: Optional[List]
    total_amount: Decimal  # calculated from quotation_snapshot if needed
    customer_name: Optional[str]

class ReadyToInvoiceResponse(BaseModel):
    quotations: List[QuotationReadyResponse]
    sales_orders: List[SalesOrderReadyResponse]


from pydantic import BaseModel

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
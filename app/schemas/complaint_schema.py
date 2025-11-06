# app/schemas/billing_schemas/complaint_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.complaint_models import ComplaintStatus, ComplaintPriority

class ComplaintBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: ComplaintStatus = ComplaintStatus.OPEN
    priority: ComplaintPriority = ComplaintPriority.MEDIUM

class ComplaintCreate(ComplaintBase):
    customer_id: int
    invoice_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    quotation_id: Optional[int] = None
    product_id: Optional[int] = None

class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    description: Optional[str] = None
    

class ComplaintResponse(ComplaintBase):
    id: int
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None

    invoice_id: Optional[int]
    sales_order_id: Optional[int]
    quotation_id: Optional[int]
    product_id: Optional[int]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

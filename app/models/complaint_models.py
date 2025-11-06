# app/models/complaint_models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base
import enum

class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class ComplaintPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id  = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SAEnum(ComplaintStatus), default=ComplaintStatus.OPEN, nullable=False)
    priority = Column(SAEnum(ComplaintPriority), default=ComplaintPriority.MEDIUM, nullable=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    customer = relationship("Customer", back_populates="complaints", lazy="joined")
    invoice = relationship("Invoice", back_populates="complaints", lazy="selectin")
    sales_order = relationship("SalesOrder", back_populates="complaints", lazy="selectin")
    quotation = relationship("Quotation", back_populates="complaints", lazy="selectin")
    @property
    def customer_name(self):
        return self.customer.name if self.customer else "N/A"

    @property
    def customer_phone(self):
        return self.customer.phone if self.customer else None

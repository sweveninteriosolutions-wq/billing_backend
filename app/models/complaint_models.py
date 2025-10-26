# app/models/billing_models/complaint_models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.db import Base
from sqlalchemy.sql import func
import enum
from sqlalchemy import Enum as SAEnum

class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ComplaintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)

    # Complaint details
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SAEnum(ComplaintStatus), default=ComplaintStatus.OPEN, nullable=False)
    priority = Column(SAEnum(ComplaintPriority), default=ComplaintPriority.MEDIUM, nullable=False)

    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    is_deleted = Column(Boolean, default=False)

    # Relationships
    customer = relationship("Customer", back_populates="complaints", lazy="selectin")
    invoice = relationship("Invoice", back_populates="complaints", lazy="selectin")
    sales_order = relationship("SalesOrder", back_populates="complaints", lazy="selectin")
    quotation = relationship("Quotation", back_populates="complaints", lazy="selectin")

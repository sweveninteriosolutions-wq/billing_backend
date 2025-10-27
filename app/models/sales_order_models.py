# app/models/billing_models/sales_order_models.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from app.core.db import Base


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    quotation_snapshot = Column(JSON, nullable=True)

    # Snapshot info
    customer_name = Column(String, nullable=True)  # snapshot of customer name at order creation

    # Workflow & flags
    completion_flag = Column(Boolean, default=False)
    completion_status = Column(MutableList.as_mutable(JSON), default=list)  # [{"date":..., "status":..., "note":...}]

    approved = Column(Boolean, default=False)
    moved_to_invoice = Column(Boolean, default=False)

    # ✅ Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ✅ Relationships
    customer = relationship("Customer", back_populates="sales_orders")
    quotation = relationship("Quotation", back_populates="sales_orders")
    invoices = relationship("Invoice", back_populates="sales_order", cascade="all, delete-orphan", lazy="selectin")
    complaints = relationship("Complaint", back_populates="sales_order", cascade="all, delete-orphan", lazy="selectin")

    created_by_user = relationship("User", foreign_keys=[created_by], lazy="selectin")
    updated_by_user = relationship("User", foreign_keys=[updated_by], lazy="selectin")

    def __repr__(self):
        return f"<SalesOrder(id={self.id}, customer='{self.customer_name}', approved={self.approved})>"

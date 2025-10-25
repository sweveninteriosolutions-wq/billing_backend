# app/models/billing_models/sales_order_models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base
from sqlalchemy.ext.mutable import MutableList

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    quotation_items = Column(JSON, nullable=True)  # <-- make sure this column exists

    # Snapshot info
    customer_name = Column(String, nullable=True)  # snapshot of customer name at order creation

    # Workflow & flags
    completion_flag = Column(Boolean, default=False)
    completion_status = Column(MutableList.as_mutable(JSON), default=list)  # [{"date":..., "status":..., "note":...}]

    approved = Column(Boolean, default=False)
    moved_to_invoice = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="sales_orders")
    quotation = relationship("Quotation", back_populates="sales_orders")
    

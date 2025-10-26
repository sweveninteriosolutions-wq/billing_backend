from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    quotations = relationship("Quotation", back_populates="customer", cascade="all, delete-orphan", lazy="joined")
    sales_orders = relationship("SalesOrder", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    invoices = relationship("Invoice", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    loyalty_tokens = relationship("LoyaltyToken", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    complaints = relationship("Complaint", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")

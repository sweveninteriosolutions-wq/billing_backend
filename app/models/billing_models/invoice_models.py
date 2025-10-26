# app/models/billing_models/invoice_models.py
from datetime import datetime
from decimal import Decimal
import enum
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, DateTime, Boolean, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base

class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    APPROVED = "approved"
    CANCELLED = "cancelled"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)

    total_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    discounted_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_paid = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    balance_due = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    status = Column(Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.PENDING, nullable=False)
    approved_by_admin = Column(Boolean, default=False)
    loyalty_claimed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # relationships
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")
    loyalty_tokens = relationship("LoyaltyToken", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")
    customer = relationship("Customer", back_populates="invoices", lazy="selectin")
    quotation = relationship("Quotation", back_populates="invoices", lazy="selectin")
    sales_order = relationship("SalesOrder", back_populates="invoices", lazy="selectin")

# keep Payment and LoyaltyToken models in same module or separate as you prefer
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)

    amount = Column(Numeric(14, 2), nullable=False)
    payment_method = Column(String, nullable=True)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="payments", lazy="joined")
    customer = relationship("Customer", back_populates="payments", lazy="selectin")

class LoyaltyToken(Base):
    __tablename__ = "loyalty_tokens"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="loyalty_tokens", lazy="selectin")
    invoice = relationship("Invoice", back_populates="loyalty_tokens", lazy="selectin")

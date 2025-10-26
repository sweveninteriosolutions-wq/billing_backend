from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, DateTime, Boolean
)
from sqlalchemy.orm import relationship
from app.core.db import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)

    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discounted_amount = Column(Numeric(10, 2), nullable=True, default=0)
    total_paid = Column(Numeric(10, 2), nullable=False, default=0)
    balance_due = Column(Numeric(10, 2), nullable=False, default=0)

    status = Column(String, default="pending")
    approved_by_admin = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")
    loyalty_tokens = relationship("LoyaltyToken", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")

    customer = relationship("Customer", back_populates="invoices", lazy="selectin")
    quotation = relationship("Quotation", back_populates="invoices", lazy="selectin")
    sales_order = relationship("SalesOrder", back_populates="invoices", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String, nullable=True)
    payment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    invoice = relationship("Invoice", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")


class LoyaltyToken(Base):
    __tablename__ = "loyalty_tokens"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="loyalty_tokens", lazy="selectin")
    invoice = relationship("Invoice", back_populates="loyalty_tokens", lazy="selectin")

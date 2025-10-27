# app/models/quotation_models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, JSON, Numeric, event, func
)
from sqlalchemy.orm import relationship
from app.core.db import Base
from decimal import Decimal

GST_RATE = Decimal("0.18")  # use Decimal for arithmetic

# ==================================================
# QUOTATION MODEL
# ==================================================
class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    quotation_number = Column(String, unique=True, nullable=False)
    issue_date = Column(DateTime(timezone=True), default=func.now())

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    description = Column(String, nullable=True)

    # Financial fields
    total_items_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    gst_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(12, 2), default=Decimal("0.00"))

    # Notes & status
    notes = Column(String, nullable=True)
    approved = Column(Boolean, default=False)
    moved_to_sales = Column(Boolean, default=False)
    moved_to_invoice = Column(Boolean, default=False)
    additional_data = Column(JSON, nullable=True)

    # Audit fields
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    customer = relationship("Customer", back_populates="quotations")
    items = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    sales_orders = relationship(
        "SalesOrder",
        back_populates="quotation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    invoices = relationship("Invoice", back_populates="quotation", cascade="all, delete-orphan", lazy="selectin")
    complaints = relationship("Complaint", back_populates="quotation", cascade="all, delete-orphan", lazy="selectin")

    # ----------------------
    # Total calculation
    # ----------------------
    def calculate_totals(self):
        total_items = sum(
            (item.total or Decimal("0.00")) for item in self.items if not item.is_deleted
        )
        gst = total_items * GST_RATE
        self.total_items_amount = total_items
        self.gst_amount = gst
        self.total_amount = total_items + gst


# Auto-update totals when items are appended or removed
@event.listens_for(Quotation.items, "append")
@event.listens_for(Quotation.items, "remove")
def update_quotation_total(target, value, initiator):
    target.calculate_totals()


# ==================================================
# QUOTATION ITEM MODEL
# ==================================================
class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"))
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)

    # Audit fields
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    quotation = relationship("Quotation", back_populates="items")

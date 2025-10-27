# app/models/grn_models.py
from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey,
    DateTime, Boolean, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base

class GRN(Base):
    __tablename__ = "grns"

    id = Column(Integer, primary_key=True, index=True)

    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), index=True, nullable=True)
    purchase_order = Column(String(100), nullable=True)
    sub_total = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    bill_number = Column(String(100), nullable=True)
    bill_file = Column(String(255), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="grns", lazy="selectin")
    items = relationship("GRNItem", back_populates="grn", cascade="all, delete-orphan", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="selectin")

    __table_args__ = (
        Index("ix_grn_supplier_status", "supplier_id", "status"),
    )

    def __repr__(self):
        return f"<GRN(id={self.id}, supplier_id={self.supplier_id}, status='{self.status}')>"

class GRNItem(Base):
    __tablename__ = "grn_items"

    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("grns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    grn = relationship("GRN", back_populates="items", lazy="selectin")
    product = relationship("Product", back_populates="grn_items", lazy="selectin")

    __table_args__ = (
        CheckConstraint(quantity > 0, name="check_grn_item_quantity_positive"),
        CheckConstraint(price >= 0, name="check_grn_item_price_non_negative"),
        Index("ix_grn_item_grn_product", "grn_id", "product_id"),
    )

    def __repr__(self):
        return f"<GRNItem(id={self.id}, grn_id={self.grn_id}, product_id={self.product_id})>"

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Text,
    CheckConstraint, Index, Boolean, Enum, func
)
from sqlalchemy.orm import relationship
from app.core.db import Base
import enum

# --------------------------
# Enums
# --------------------------
class LocationEnum(str, enum.Enum):
    showroom = "showroom"
    warehouse = "warehouse"

# --------------------------
# Product
# --------------------------
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    quantity_showroom = Column(Integer, default=0, nullable=False)
    quantity_warehouse = Column(Integer, default=0, nullable=False)
    min_stock_threshold = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # False = active, True = deleted

    __table_args__ = (
        CheckConstraint(price >= 0, name="check_product_price_non_negative"),
        CheckConstraint(quantity_showroom >= 0, name="check_quantity_showroom_non_negative"),
        CheckConstraint(quantity_warehouse >= 0, name="check_quantity_warehouse_non_negative"),
    )

    grn_items = relationship("GRNItem", back_populates="product")
    stock_transfers = relationship("StockTransfer", back_populates="product")


# --------------------------
# Supplier
# --------------------------
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # False = active, True = deleted

    grns = relationship("GRN", back_populates="supplier")


# --------------------------
# GRN and GRN Items
# --------------------------
class GRN(Base):
    __tablename__ = "grns"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    purchase_order = Column(String, nullable=True)
    sub_total = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    bill_number = Column(String, nullable=True)
    bill_file = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending", nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # False = active, True = deleted

    supplier = relationship("Supplier", back_populates="grns")
    items = relationship("GRNItem", back_populates="grn", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="joined")


class GRNItem(Base):
    __tablename__ = "grn_items"

    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("grns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(quantity > 0, name="check_grn_item_quantity_positive"),
        CheckConstraint(price >= 0, name="check_grn_item_price_non_negative"),
    )

    grn = relationship("GRN", back_populates="items")
    product = relationship("Product", back_populates="grn_items")


# --------------------------
# Stock Transfer
# --------------------------
class StockTransfer(Base):
    __tablename__ = "stock_transfers"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    from_location = Column(Enum(LocationEnum), nullable=False)
    to_location = Column(Enum(LocationEnum), nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)
    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    transfer_date = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # False = active, True = deleted
    __table_args__ = (
        CheckConstraint(quantity > 0, name="check_transfer_quantity_positive"),
    )
    product = relationship("Product", back_populates="stock_transfers")
    transfer_user = relationship("User", foreign_keys=[transferred_by], lazy="joined")
    complete_user = relationship("User", foreign_keys=[completed_by], lazy="joined")


# --------------------------
# Index Optimization
# --------------------------
Index("ix_product_name_category", Product.name, Product.category)
Index("ix_grn_supplier_status", GRN.supplier_id, GRN.status)
Index("ix_transfer_product_status", StockTransfer.product_id, StockTransfer.status)

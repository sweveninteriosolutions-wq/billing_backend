# app/models/product_models.py
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, CheckConstraint, Index,
    ForeignKey, DateTime, func
)
from sqlalchemy.orm import relationship
from app.core.db import Base
import enum

class LocationEnum(str, enum.Enum):
    showroom = "showroom"
    warehouse = "warehouse"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    quantity_showroom = Column(Integer, default=0, nullable=False)
    quantity_warehouse = Column(Integer, default=0, nullable=False)
    min_stock_threshold = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    supplier = relationship("Supplier", back_populates="products", lazy="selectin")

    grn_items = relationship("GRNItem", back_populates="product", lazy="selectin")
    stock_transfers = relationship("StockTransfer", back_populates="product", lazy="selectin")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by_user = relationship("User", foreign_keys=[created_by], lazy="selectin")
    updated_by_user = relationship("User", foreign_keys=[updated_by], lazy="selectin")

    __table_args__ = (
        CheckConstraint(price >= 0, name="check_product_price_non_negative"),
        CheckConstraint(quantity_showroom >= 0, name="check_quantity_showroom_non_negative"),
        CheckConstraint(quantity_warehouse >= 0, name="check_quantity_warehouse_non_negative"),
        Index("ix_product_name_category", "name", "category"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}')>"

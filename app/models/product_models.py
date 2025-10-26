from sqlalchemy import Column, Integer, String, Float, Boolean, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.core.db import Base
import enum

# --------------------------
# Enums
# --------------------------
class LocationEnum(str, enum.Enum):
    showroom = "showroom"
    warehouse = "warehouse"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    quantity_showroom = Column(Integer, default=0, nullable=False)
    quantity_warehouse = Column(Integer, default=0, nullable=False)
    min_stock_threshold = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(price >= 0, name="check_product_price_non_negative"),
        CheckConstraint(quantity_showroom >= 0, name="check_quantity_showroom_non_negative"),
        CheckConstraint(quantity_warehouse >= 0, name="check_quantity_warehouse_non_negative"),
        Index("ix_product_name_category", name, category),
    )
    
    grn_items = relationship("GRNItem", back_populates="product")
    stock_transfers = relationship("StockTransfer", back_populates="product")


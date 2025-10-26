 
from sqlalchemy import Column, Integer, Enum, String, ForeignKey, DateTime, Boolean, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base
import enum

class LocationEnum(str, enum.Enum):
    showroom = "showroom"
    warehouse = "warehouse"

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
    is_deleted = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
            CheckConstraint(quantity > 0, name="check_transfer_quantity_positive"),
            Index("ix_transfer_product_status", product_id, status),
        )
    product = relationship("Product", back_populates="stock_transfers")
    transfer_user = relationship("User", foreign_keys=[transferred_by], lazy="selectin")
    complete_user = relationship("User", foreign_keys=[completed_by], lazy="selectin")
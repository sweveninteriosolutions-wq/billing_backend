# app/models/stock_transfer_models.py
from sqlalchemy import (
    Column, Integer, Enum, String, ForeignKey, DateTime, Boolean,
    CheckConstraint, Index, func, select
)
from sqlalchemy.orm import relationship
from app.core.db import Base
import enum

class LocationEnum(str, enum.Enum):
    showroom = "showroom"
    warehouse = "warehouse"

class TransferStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)

    from_location = Column(Enum(LocationEnum), nullable=False)
    to_location = Column(Enum(LocationEnum), nullable=False)
    status = Column(Enum(TransferStatus), default=TransferStatus.pending, nullable=False, index=True)

    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    transfer_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    is_deleted = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_transfer_quantity_positive"),
        Index("ix_transfer_product_status", "product_id", "status"),
    )

    product = relationship("Product", back_populates="stock_transfers")
    transfer_user = relationship("User", foreign_keys=[transferred_by], lazy="selectin")
    complete_user = relationship("User", foreign_keys=[completed_by], lazy="selectin")
    created_user = relationship("User", foreign_keys=[created_by], lazy="selectin")
    updated_user = relationship("User", foreign_keys=[updated_by], lazy="selectin")

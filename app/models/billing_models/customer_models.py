from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.core.db import Base
from sqlalchemy import ForeignKey

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)  # Soft delete flag
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User ID who created the customer
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User ID who last updated the customer
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

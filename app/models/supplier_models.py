# app/models/supplier_models.py
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False, unique=True, index=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    grns = relationship("GRN", back_populates="supplier", lazy="selectin")
    products = relationship("Product", back_populates="supplier", lazy="selectin")


    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined", backref="suppliers_created")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="joined", backref="suppliers_updated")

    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}')>"

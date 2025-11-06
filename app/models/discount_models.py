from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean
from app.core.db import Base
from sqlalchemy.orm import relationship

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    discount_type = Column(String(20), nullable=False)  # 'percentage' or 'flat'
    discount_value = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="active")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    note = Column(String(255), nullable=True)

    # New Soft Delete Flag
    is_deleted = Column(Boolean, default=False)

    invoices = relationship("Invoice", back_populates="discount", lazy="selectin")

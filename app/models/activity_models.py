# app/models/activity_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class UserActivity(Base):
    __tablename__ = "user_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String, nullable=False)    
       
    message = Column(String, nullable=False)      
    created_at = Column(DateTime(timezone=True), server_default=func.now())

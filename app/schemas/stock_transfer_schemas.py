# app/schemas/stock_transfer_schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.stock_transfer_models import LocationEnum, TransferStatus

class StockTransferBase(BaseModel):
    product_id: int
    quantity: int
    from_location: LocationEnum
    to_location: LocationEnum

class StockTransferCreate(StockTransferBase):
    pass

class StockTransferUpdate(BaseModel):
    status: Optional[TransferStatus] = None
    completed_by: Optional[int] = None

class StockTransferOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    from_location: LocationEnum
    to_location: LocationEnum
    status: TransferStatus
    transfer_date: datetime
    completed_at: Optional[datetime]
    is_deleted: bool

    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# --------------------------
# Generic Message Response
# --------------------------
class MessageResponse(BaseModel):
    message: str

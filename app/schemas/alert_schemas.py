from pydantic import BaseModel
from typing import List

class StockAlert(BaseModel):
    product_id: int
    product_name: str
    quantity_showroom: int
    quantity_total: int
    min_stock_threshold: int

    class Config:
        from_attributes = True

class StockAlertListResponse(BaseModel):
    message: str
    data: List[StockAlert]

from pydantic import BaseModel, Field
from typing import Optional
from typing_extensions import Annotated
from datetime import date
from decimal import Decimal

PositiveDecimal = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]

class DiscountBase(BaseModel):
    name: str
    code: str
    discount_type: str = Field(..., pattern="^(percentage|flat)$")
    discount_value: NonNegativeDecimal
    status: str = Field(default="active")
    start_date: date
    end_date: date
    usage_limit: Optional[int] = None
    note: Optional[str] = None

class DiscountCreate(DiscountBase):
    pass

class DiscountUpdate(BaseModel):
    name: Optional[str]
    code: Optional[str]
    discount_type: Optional[str]
    discount_value: Optional[NonNegativeDecimal]
    status: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    usage_limit: Optional[int]
    note: Optional[str]

class DiscountOut(DiscountBase):
    id: int
    used_count: int
    is_deleted: bool

    class Config:
        orm_mode = True

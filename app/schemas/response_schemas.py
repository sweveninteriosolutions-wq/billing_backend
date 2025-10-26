# app/schemas/response_schemas.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
from pydantic.generics import GenericModel

T = TypeVar("T")

class ResponseMessage(GenericModel, Generic[T]):
    message: str
    data: Optional[T] = None

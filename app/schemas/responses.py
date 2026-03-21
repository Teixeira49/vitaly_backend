from typing import Generic, TypeVar, Optional, List, Union, Any
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    size: int
    total: int
    total_pages: int

class ErrorDetail(BaseModel):
    loc: Optional[List[Union[str, int]]] = None
    msg: str
    type: str

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[ErrorDetail]] = None
    meta: Optional[PaginationMeta] = None

    class Config:
        from_attributes = True

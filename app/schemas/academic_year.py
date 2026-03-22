from pydantic import BaseModel
from datetime import date
from typing import Optional

class AcademicYearCreate(BaseModel):
    start_date: date
    end_date: date

class AcademicYearResponse(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool
    is_active: bool
    is_deleted: bool

    class Config:
        from_attributes = True

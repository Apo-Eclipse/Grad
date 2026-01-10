from typing import Any, Dict, Optional
from datetime import datetime

from ninja import Schema
from pydantic import root_validator


class IncomeSchema(Schema):
    id: int
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None
    created_at: datetime


class IncomeCreateSchema(Schema):
    type_income: str
    amount: float
    description: Optional[str] = None


class IncomeUpdateSchema(Schema):
    type_income: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

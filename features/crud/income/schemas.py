from typing import Any, Dict, Optional
from ninja import Schema
from pydantic import root_validator


class IncomeCreateSchema(Schema):
    type_income: str
    amount: float
    description: Optional[str] = None


class IncomeUpdateSchema(Schema):
    type_income: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    active: Optional[bool] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

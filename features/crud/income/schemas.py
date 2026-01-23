from typing import Any, Dict, Optional
from ninja import Schema
from pydantic import model_validator


class IncomeCreateSchema(Schema):
    type_income: str
    amount: float
    description: Optional[str] = None


class IncomeUpdateSchema(Schema):
    type_income: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


class IncomeOutSchema(Schema):
    id: int
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None
    active: bool
    created_at: Any
    updated_at: Any
    icon: Optional[str] = "cash-outline"
    color: Optional[str] = "#10b981"


class IncomeResponse(Schema):
    status: str
    message: str
    data: Optional[IncomeOutSchema] = None


class IncomeListResponse(Schema):
    status: str
    message: str
    data: list[IncomeOutSchema]

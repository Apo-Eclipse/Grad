from typing import Any, Optional

from ninja import Schema
from pydantic import Field, model_validator


class BudgetCreateSchema(Schema):
    name: str  # Frontend sends "name", maps to budget_name
    description: Optional[str] = None
    icon: Optional[str] = "wallet"
    color: Optional[str] = "#3162ff"
    total_limit: float = Field(default=0.0)
    priority_level_int: Optional[int] = None


class BudgetUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    total_limit: Optional[float] = None
    priority_level_int: Optional[int] = None
    active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


# Base CRUD output (raw data only)
class BudgetOutSchema(Schema):
    id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float
    priority_level_int: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    active: bool
    created_at: Any
    updated_at: Any


class BudgetResponse(Schema):
    status: str
    message: str
    data: Optional[BudgetOutSchema] = None


class BudgetListResponse(Schema):
    status: str
    message: str
    data: list[BudgetOutSchema]

from typing import Any, Dict, Optional
from datetime import datetime

from ninja import Schema
from pydantic import Field, root_validator


class BudgetSchema(Schema):
    id: int
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float
    priority_level_int: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class BudgetCreateSchema(Schema):
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float = Field(default=0.0)
    priority_level_int: Optional[int] = None
    is_active: bool = Field(default=True)


class BudgetUpdateSchema(Schema):
    budget_name: Optional[str] = None
    description: Optional[str] = None
    total_limit: Optional[float] = None
    priority_level_int: Optional[int] = None
    is_active: Optional[bool] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

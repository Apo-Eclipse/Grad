from typing import Any, Dict, Optional
from datetime import date
from ninja import Schema
from pydantic import Field, root_validator


class GoalCreateSchema(Schema):
    goal_name: str
    description: Optional[str] = None
    target: float = Field(default=0.0)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    active: bool = True
    plan: Optional[str] = None


class GoalUpdateSchema(Schema):
    goal_name: Optional[str] = None
    description: Optional[str] = None
    target: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    active: Optional[bool] = None
    plan: Optional[str] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

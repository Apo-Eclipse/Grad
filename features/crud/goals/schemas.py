from typing import Any, Dict, Optional
from datetime import date, datetime

from ninja import Schema
from pydantic import Field, root_validator


class GoalSchema(Schema):
    id: int
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: float
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str
    plan: Optional[str] = None
    created_at: datetime


class GoalCreateSchema(Schema):
    goal_name: str
    description: Optional[str] = None
    target: float = Field(default=0.0)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str = Field(default="active")
    plan: Optional[str] = None


class GoalUpdateSchema(Schema):
    goal_name: Optional[str] = None
    description: Optional[str] = None
    target: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    plan: Optional[str] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

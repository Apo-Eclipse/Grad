from typing import Any, Optional
from datetime import date
from ninja import Schema
from pydantic import Field, model_validator


class GoalCreateSchema(Schema):
    name: str  # Frontend sends "name"
    target: float = Field(default=0.0)
    description: Optional[str] = "No description yet"
    due_date: Optional[date] = None
    plan: Optional[str] = None
    status: Optional[str] = None  # Frontend sends "status" ("active" etc)
    icon: Optional[str] = "flag-outline"
    color: Optional[str] = "#10b981"
    start_date: Optional[date] = None
    active: bool = True


class GoalUpdateSchema(Schema):
    name: Optional[str] = None
    target: Optional[float] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    saved_amount: Optional[float] = None
    active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


# Base CRUD output (raw data only)
class GoalOutSchema(Schema):
    id: int
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: float
    saved_amount: float
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    plan: Optional[str] = None
    active: bool
    created_at: Any
    updated_at: Any


class GoalResponse(Schema):
    status: str
    message: str
    data: Optional[GoalOutSchema] = None


class GoalListResponse(Schema):
    status: str
    message: str
    data: list[GoalOutSchema]

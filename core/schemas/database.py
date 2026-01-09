"""Database schemas."""

from datetime import date, datetime
from typing import Any, Dict, Optional

from ninja import Schema
from pydantic import Field, root_validator, validator

from ..models import EMPLOYMENT_OPTIONS, EDUCATION_OPTIONS, GENDER_OPTIONS


class TransactionSchema(Schema):
    id: int
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    created_at: datetime


class TransactionCreateSchema(Schema):
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None


class TransactionUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


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
    user_id: int
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


class UserSchema(Schema):
    id: int
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: str
    birthday: date
    gender: str
    employment_status: str
    education_level: str
    created_at: datetime


class UserCreateSchema(Schema):
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: str
    birthday: date
    gender: str
    employment_status: str
    education_level: str

    @validator("gender")
    def validate_gender(cls, v):
        if v not in GENDER_OPTIONS:
            raise ValueError(
                f"Invalid gender. Must be one of: {list(GENDER_OPTIONS.keys())}"
            )
        return v

    @validator("employment_status")
    def validate_employment_status(cls, v):
        if v not in EMPLOYMENT_OPTIONS:
            raise ValueError(
                f"Invalid employment_status. Must be one of: {list(EMPLOYMENT_OPTIONS.keys())}"
            )
        return v

    @validator("education_level")
    def validate_education_level(cls, v):
        if v not in EDUCATION_OPTIONS:
            raise ValueError(
                f"Invalid education_level. Must be one of: {list(EDUCATION_OPTIONS.keys())}"
            )
        return v


class IncomeSchema(Schema):
    id: int
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None
    created_at: datetime


class IncomeCreateSchema(Schema):
    user_id: int
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


class ConversationSchema(Schema):
    conversation_id: int
    user_id: int
    title: Optional[str] = None
    channel: Optional[str] = None
    started_at: datetime
    last_message_at: Optional[datetime] = None


class MessageSchema(Schema):
    message_id: int
    conversation_id: int
    sender_type: str
    content: str
    content_type: str
    created_at: datetime

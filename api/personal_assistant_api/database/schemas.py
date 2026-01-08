"""Database schemas."""
from datetime import date, datetime
from typing import Any, Dict, Literal, Optional

from ninja import Schema
from pydantic import Field, root_validator


class TransactionSchema(Schema):
    transaction_id: int
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
    budget_id: int
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
    goal_id: int
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


class UserSchema(Schema):
    user_id: int
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
    user_id: Optional[int] = None
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: str
    birthday: date
    gender: str
    employment_status: Literal[
        "Employed Full-time", "Employed Part-time", "Unemployed", "Retired", "Student"
    ]
    education_level: str


class IncomeSchema(Schema):
    income_id: int
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

"""Database schemas for Personal Assistant API."""
from ninja import Schema
from pydantic import Field, validator
from typing import Optional, List, Literal, Dict, Any
from datetime import date, time, datetime
from decimal import Decimal


# ============ TRANSACTION SCHEMAS ============
class TransactionSchema(Schema):
    transaction_id: int
    date: date
    amount: float
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    neighbourhood: Optional[str] = None
    type_spending: Optional[str] = None
    user_id: int
    budget_id: Optional[int] = None
    budget_name: Optional[str] = None  # From JOIN with budget table
    created_at: Optional[datetime] = None


class TransactionCreateSchema(Schema):
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None  # Accept as string instead of time object
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

    @validator('*', pre=True, always=True)
    def at_least_one_field(cls, v, values):
        # This will be checked after all values are parsed
        return v


# ============ BUDGET SCHEMAS ============
class BudgetSchema(Schema):
    budget_id: int
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float
    priority_level_int: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BudgetCreateSchema(Schema):
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float = Field(default=0)
    priority_level_int: Optional[int] = None
    is_active: bool = Field(default=True)


# ============ GOAL SCHEMAS ============
class GoalSchema(Schema):
    goal_id: int
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: float
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GoalCreateSchema(Schema):
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: float = Field(default=0)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str = Field(default="active")


# ============ USER SCHEMAS ============
class UserSchema(Schema):
    user_id: int
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    employment_status: Optional[str] = None
    education_level: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserCreateSchema(Schema):
    user_id: Optional[int] = None  # Optional: allow custom user_id or auto-generate
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


# ============ INCOME SCHEMAS ============
class IncomeSchema(Schema):
    income_id: int
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IncomeCreateSchema(Schema):
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None


# ============ CONVERSATION SCHEMAS ============
class ConversationSchema(Schema):
    conversation_id: int
    user_id: int
    title: Optional[str] = None
    channel: str = "web"
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    summary_text: Optional[str] = None


class ConversationStartSchema(Schema):
    user_id: int
    channel: str = Field(default="web")


class MessageSchema(Schema):
    message_id: int
    conversation_id: int
    sender_type: str
    source_agent: Optional[str] = None
    content: str
    content_type: str = "text"
    language: str = "en"
    created_at: Optional[datetime] = None


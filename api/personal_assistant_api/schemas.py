"""Request and response schemas."""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, Field, root_validator


class AnalysisRequestSchema(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


class AnalysisResponseSchema(BaseModel):
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(BaseModel):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationStartSchema(BaseModel):
    user_id: int
    channel: str = Field(default="web")


class ConversationResponseSchema(BaseModel):
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime


class TransactionCreateSchema(BaseModel):
    user_id: int
    date: date
    amount: Decimal
    time: Optional[str] = None  # Accept as string instead of time object
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None


class TransactionUpdateSchema(BaseModel):
    date: Optional[date] = None
    amount: Optional[Decimal] = None
    time: Optional[str] = None  # Accept as string instead of time object
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


class BudgetCreateSchema(BaseModel):
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: Decimal = Field(default=0)
    priority_level_int: Optional[int] = None
    is_active: bool = Field(default=True)


class GoalCreateSchema(BaseModel):
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: Decimal = Field(default=0)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str = Field(default="active")
    plan: Optional[str] = None


class UserCreateSchema(BaseModel):
    user_id: Optional[int] = None  # Optional: allow custom user_id or auto-generate
    first_name: str  # TEXT NOT NULL
    last_name: str  # TEXT NOT NULL
    job_title: Optional[str] = None  # TEXT (nullable)
    address: str  # TEXT NOT NULL
    birthday: date  # DATE NOT NULL
    gender: str  # gender_type (not null, enum)
    employment_status: Literal[
        "Employed Full-time", "Employed Part-time", "Unemployed", "Retired", "Student"
    ]
    education_level: str  # edu_level (not null, enum)


class IncomeCreateSchema(BaseModel):
    user_id: int
    type_income: str
    amount: Decimal
    description: Optional[str] = None


class GoalMakerRequestSchema(BaseModel):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class GoalMakerResponseSchema(BaseModel):
    conversation_id: int
    message: str
    goal_name: Optional[str] = None
    target: Optional[float] = None
    goal_description: Optional[str] = None
    due_date: Optional[str] = None
    plan: Optional[str] = None
    is_done: bool = False


class BudgetMakerRequestSchema(BaseModel):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class BudgetMakerResponseSchema(BaseModel):
    conversation_id: int
    message: str
    budget_name: Optional[str] = None
    total_limit: Optional[float] = None
    description: Optional[str] = None
    priority_level_int: Optional[int] = None
    is_done: bool = False


class TransactionMakerRequestSchema(BaseModel):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class TransactionMakerResponseSchema(BaseModel):
    conversation_id: int
    message: str
    amount: Optional[float] = None
    budget_id: Optional[int] = None
    store_name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    city: Optional[str] = None
    neighbourhood: Optional[str] = None
    type_spending: Optional[str] = None
    is_done: bool = False

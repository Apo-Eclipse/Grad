from ninja import Schema
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal

class TransactionSchema(Schema):
    transaction_id: int
    date: date
    amount: float
    time: Optional[time] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    neighbourhood: Optional[str] = None
    type_spending: Optional[str] = None
    user_id: int
    budget_id: Optional[int] = None
    created_at: Optional[datetime] = None

class TransactionCreateSchema(Schema):
    date: date
    amount: float
    time: Optional[time] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    neighbourhood: Optional[str] = None
    type_spending: Optional[str] = None
    user_id: int
    budget_id: Optional[int] = None

class BudgetSchema(Schema):
    budget_id: int
    user_id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float
    priority_level_int: Optional[int] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GoalSchema(Schema):
    goal_id: int
    user_id: int
    goal_name: str
    description: Optional[str] = None
    target: float
    current: float
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserSchema(Schema):
    user_id: int
    first_name: str
    last_name: str
    job_title: str
    address: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class IncomeSchema(Schema):
    income_id: int
    user_id: int
    type_income: str
    amount: float
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

"""Schemas for specialized Maker agents."""
from typing import Literal, Optional
from ninja import Schema


# --- Goal Maker ---
class GoalMakerRequestSchema(Schema):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class GoalMakerResponseSchema(Schema):
    conversation_id: int
    message: str
    goal_name: Optional[str] = None
    target: Optional[float] = None
    goal_description: Optional[str] = None
    due_date: Optional[str] = None
    plan: Optional[str] = None
    is_done: bool = False


# --- Budget Maker ---
class BudgetMakerRequestSchema(Schema):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class BudgetMakerResponseSchema(Schema):
    conversation_id: int
    message: str
    action: Literal["create", "update"] = "create"
    budget_name: Optional[str] = None
    budget_id: Optional[int] = None
    total_limit: Optional[float] = None
    description: Optional[str] = None
    priority_level_int: Optional[int] = None
    is_done: bool = False


# --- Transaction Maker ---
class TransactionMakerRequestSchema(Schema):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class TransactionMakerResponseSchema(Schema):
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

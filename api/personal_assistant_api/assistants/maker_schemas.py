"""Schemas for the Maker agents (Goal, Budget, Transaction)."""
from ninja import Schema
from pydantic import Field
from typing import Optional


class MakerRequestSchema(Schema):
    """Base request schema for maker endpoints."""
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class MakerResponseSchema(Schema):
    """Base response schema for maker endpoints."""
    response: str
    status: str = "success"


# ============ GOAL MAKER SCHEMAS ============
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
    is_done: bool = False


# ============ BUDGET MAKER SCHEMAS ============
class BudgetMakerRequestSchema(Schema):
    user_id: int
    user_request: str
    conversation_id: Optional[int] = None


class BudgetMakerResponseSchema(Schema):
    conversation_id: int
    message: str
    budget_name: Optional[str] = None
    total_limit: Optional[float] = None
    description: Optional[str] = None
    priority_level_int: Optional[int] = None
    is_done: bool = False


# ============ TRANSACTION MAKER SCHEMAS ============
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


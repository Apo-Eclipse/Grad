"""Schemas specific to the Personal Assistant agents."""

from datetime import datetime
from django.utils import timezone
from typing import Any, Dict, Optional, Literal

from ninja import Schema
from pydantic import Field


class AnalysisRequestSchema(Schema):
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[int] = None
    conversation_id: Optional[int] = None
    # user_id is now derived from auth token


class AnalysisResponseSchema(Schema):
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(Schema):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=timezone.now)


"""Schemas for specialized Maker agents."""


# --- Goal Maker ---
class GoalMakerRequestSchema(Schema):
    # user_id removed
    user_request: str
    conversation_id: Optional[int] = None


class GoalMakerResponseSchema(Schema):
    conversation_id: int
    message: str
    action: Literal["create", "update"] = "create"
    goal_name: Optional[str] = None
    goal_id: Optional[int] = None
    target: Optional[float] = None
    goal_description: Optional[str] = None
    due_date: Optional[str] = None
    plan: Optional[str] = None
    is_done: bool = False


# --- Budget Maker ---
class BudgetMakerRequestSchema(Schema):
    # user_id removed
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
    # user_id removed
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
    is_done: bool = False

from typing import Any, Dict, List, Optional
from datetime import date
from ninja import Schema


# =============================================================================
# Category/Spending Analytics
# =============================================================================


class CategoryBreakdownSchema(Schema):
    name: str
    amount: float
    count: int
    percentage: float
    color: Optional[str] = None
    icon: Optional[str] = None


class MonthlyBreakdownSchema(Schema):
    total_spent: float
    total_income: float
    net_savings: float
    surplus: bool
    transaction_count: int
    avg_per_transaction: float
    categories: List[CategoryBreakdownSchema]


class OverspendSummarySchema(Schema):
    total_income: float
    total_spent: float
    net_position: float
    is_deficit: bool
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_regular: Optional[float] = None
    total_savings: Optional[float] = None
    accounts: Optional[List[Dict[str, Any]]] = None


class OverspendResponseSchema(Schema):
    data: Optional[List[Dict[str, Any]]] = None
    summary: Optional[OverspendSummarySchema] = None


# =============================================================================
# Budget Analytics
# =============================================================================


class BudgetStatsSchema(Schema):
    id: int
    budget_name: str
    description: Optional[str] = None
    total_limit: float
    priority_level_int: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    active: bool
    created_at: Any
    updated_at: Any
    # Computed fields
    spent: float
    remaining: float
    percentage_used: float
    transaction_count: int


class BudgetStatsResponse(Schema):
    status: str
    message: str
    data: Optional[BudgetStatsSchema] = None


class BudgetStatsListResponse(Schema):
    status: str
    message: str
    data: List[BudgetStatsSchema]


# =============================================================================
# Goal Analytics
# =============================================================================


class GoalStatsSchema(Schema):
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
    # Computed fields
    progress_percentage: float
    days_remaining: Optional[int] = None


class GoalStatsResponse(Schema):
    status: str
    message: str
    data: Optional[GoalStatsSchema] = None


class GoalStatsListResponse(Schema):
    status: str
    message: str
    data: List[GoalStatsSchema]


# =============================================================================
# Transaction Analytics
# =============================================================================


class TransactionSummarySchema(Schema):
    total_amount: float
    currency: str
    count: int

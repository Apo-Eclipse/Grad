from typing import Any, Dict, List, Optional
from ninja import Schema


class CategoryBreakdownSchema(Schema):
    name: str
    amount: float
    color: str
    percentage: float
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
    # Extra fields implementation provides
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    accounts: Optional[List[Dict[str, Any]]] = None


class OverspendResponseSchema(Schema):
    data: Optional[List[Dict[str, Any]]] = None
    summary: Optional[OverspendSummarySchema] = None

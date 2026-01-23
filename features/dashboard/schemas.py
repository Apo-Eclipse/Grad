from typing import Any, Dict, List, Optional
from ninja import Schema


class DashboardBudgetSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None
    priority: int
    limit: float
    spent: float
    remaining: float
    percentage_used: float
    color: Optional[str] = None
    icon: Optional[str] = None


class DashboardSummarySchema(Schema):
    total_income: float
    total_spent: float
    net_position: float
    is_deficit: bool
    month_label: str

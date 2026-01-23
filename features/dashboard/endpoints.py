"""Dashboard endpoints for frontend visualization."""

import logging
from typing import Any, Dict, List
from .schemas import DashboardBudgetSchema, DashboardSummarySchema


from django.utils import timezone
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from ninja import Router

from core.models import Budget, Transaction, Income
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/budgets", response=List[DashboardBudgetSchema])
def get_dashboard_budgets(request):
    """
    Get budget progress for the dashboard.
    Returns budgets with spent amount, remaining, and percentage for current month.
    """
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Fetch active budgets
    budgets = Budget.objects.filter(user_id=request.user.id, active=True).order_by(
        "-priority_level_int"
    )

    # Fetch active transactions for current month
    budgets_with_spend = budgets.annotate(
        spent=Coalesce(
            Sum(
                "transaction__amount",
                filter=Q(
                    transaction__date__gte=current_month_start,
                    transaction__active=True,
                    transaction__transaction_type="EXPENSE",  # Only count expenses
                ),
            ),
            0,
            output_field=DecimalField(),
        )
    )

    results = []
    for b in budgets_with_spend:
        limit = float(b.total_limit)
        spent = float(b.spent)
        remaining = max(0, limit - spent)
        percentage_used = (spent / limit * 100) if limit > 0 else 0.0

        results.append(
            {
                "id": b.id,
                "name": b.budget_name,
                "limit": limit,
                "spent": spent,
                "remaining": remaining,
                "percentage_used": round(percentage_used, 1),
                "priority": b.priority_level_int,
                "color": b.color,
                "icon": b.icon,
                "description": b.description,
            }
        )

    return results


@router.get("/summary", response=DashboardSummarySchema)
def get_dashboard_summary(request):
    """
    Get financial summary (Net Position) for the dashboard.
    """
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_label = now.strftime("%B %Y")  # e.g. "October 2025"

    # 1. Total Income (Active)
    # The frontend sums 'incomeSources'. Assuming this means all active Income entries
    # represent monthly income logic.
    # If Income is one-off, this might be wrong, but we follow frontend logic "incomeSources list".
    total_income_agg = Income.objects.filter(
        user_id=request.user.id, active=True
    ).aggregate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))

    total_income = float(total_income_agg["total"])

    # 2. Total Spent (Active transactions, Current Month)
    total_spent_agg = Transaction.objects.filter(
        user_id=request.user.id,
        active=True,
        date__gte=current_month_start,
        transaction_type="EXPENSE",  # Only expenses count towards spend
    ).aggregate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))

    total_spent = float(total_spent_agg["total"])

    # 3. Net Position
    net_position = total_income - total_spent
    is_deficit = total_spent > total_income

    return {
        "total_income": total_income,
        "total_spent": total_spent,
        "net_position": net_position,
        "is_deficit": is_deficit,
        "month_label": month_label,
    }

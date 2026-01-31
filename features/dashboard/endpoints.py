"""Dashboard endpoints for frontend visualization."""

import logging
from typing import List
from .schemas import DashboardBudgetSchema, DashboardSummarySchema

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from ninja import Router

from core.models import Budget, Transaction, Income, Account
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/budgets", response=List[DashboardBudgetSchema])
async def get_dashboard_budgets(request):
    """
    Get budget progress for the dashboard.
    Returns budgets with spent amount, remaining, and percentage for current month.
    """
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Fetch active budgets with annotated spending
    @sync_to_async
    def fetch_budgets():
        budgets = Budget.objects.filter(user_id=request.user.id, active=True).order_by(
            "-priority_level_int"
        )
        budgets_with_spend = budgets.annotate(
            spent=Coalesce(
                Sum(
                    "transaction__amount",
                    filter=Q(
                        transaction__date__gte=current_month_start,
                        transaction__active=True,
                        transaction__transaction_type="EXPENSE",
                    ),
                ),
                0,
                output_field=DecimalField(),
            )
        )
        return list(budgets_with_spend)

    budgets_with_spend = await fetch_budgets()

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
async def get_dashboard_summary(request):
    """
    Get financial summary (Net Position) for the dashboard.
    """
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_label = now.strftime("%B %Y")  # e.g. "October 2025"

    @sync_to_async
    def fetch_summary_data():
        # 1. Total Income (Active)
        total_income_agg = Income.objects.filter(
            user_id=request.user.id, active=True
        ).aggregate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))
        total_income = float(total_income_agg["total"])

        # 2. Total Spent (Active transactions, Current Month)
        total_spent_agg = Transaction.objects.filter(
            user_id=request.user.id,
            active=True,
            date__gte=current_month_start,
            transaction_type="EXPENSE",
        ).aggregate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))
        total_spent = float(total_spent_agg["total"])

        # 3. Total Budgeted Amount
        total_budgeted_agg = Budget.objects.filter(
            user_id=request.user.id, active=True
        ).aggregate(total=Coalesce(Sum("total_limit"), 0, output_field=DecimalField()))
        total_budgeted = float(total_budgeted_agg["total"])

        # 4. Total Assets
        total_assets_agg = Account.objects.filter(
            user_id=request.user.id, active=True
        ).aggregate(total=Coalesce(Sum("balance"), 0, output_field=DecimalField()))
        total_assets = float(total_assets_agg["total"])

        return total_income, total_spent, total_budgeted, total_assets

    (
        total_income,
        total_spent,
        total_budgeted_amount,
        total_assets,
    ) = await fetch_summary_data()

    # Derived Metrics
    net_position = total_income - total_spent
    is_deficit = total_spent > total_income
    day_of_month = now.day
    daily_average_spend = (total_spent / day_of_month) if day_of_month > 0 else 0.0
    spend_percentage = (total_spent / total_income * 100) if total_income > 0 else 0.0
    budget_allocation_percentage = (
        (total_budgeted_amount / total_income * 100) if total_income > 0 else 0.0
    )

    return {
        "total_income": total_income,
        "total_spent": total_spent,
        "net_position": net_position,
        "is_deficit": is_deficit,
        "month_label": month_label,
        "daily_average_spend": round(daily_average_spend, 2),
        "spend_percentage": round(spend_percentage, 1),
        "total_budgeted_amount": total_budgeted_amount,
        "budget_allocation_percentage": round(budget_allocation_percentage, 1),
        "total_assets": total_assets,
    }

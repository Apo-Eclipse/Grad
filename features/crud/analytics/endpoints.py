"""Analytics endpoints - Aggregations, computed fields, and advanced queries."""

import logging
from typing import Any, Dict, Optional

from ninja import Router, Query
from django.db.models import Sum, DecimalField, Count, Q
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from core.models import Transaction, Budget, Income, Goal, Account
from core.utils.responses import success_response, error_response
from features.auth.api import AuthBearer
from .schemas import (
    MonthlyBreakdownSchema,
    OverspendResponseSchema,
    BudgetStatsResponse,
    BudgetStatsListResponse,
    GoalStatsResponse,
    GoalStatsListResponse,
    TransactionSummarySchema,
)

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# =============================================================================
# Budget Analytics
# =============================================================================


def _compute_budget_stats(budget_obj, spent_amount, tx_count) -> dict:
    """Compute derived fields for a budget object."""
    limit = float(budget_obj.total_limit)
    spent = float(spent_amount) if spent_amount else 0.0
    remaining = max(0, limit - spent)
    percentage_used = (spent / limit * 100) if limit > 0 else 0.0

    return {
        "id": budget_obj.id,
        "budget_name": budget_obj.budget_name,
        "description": budget_obj.description,
        "total_limit": limit,
        "priority_level_int": budget_obj.priority_level_int,
        "icon": budget_obj.icon,
        "color": budget_obj.color,
        "active": budget_obj.active,
        "created_at": budget_obj.created_at,
        "updated_at": budget_obj.updated_at,
        # Computed
        "spent": spent,
        "remaining": remaining,
        "percentage_used": round(percentage_used, 1),
        "transaction_count": tx_count,
    }


@router.get("/budgets/stats", response=BudgetStatsListResponse)
def get_budget_stats(request, active: Optional[bool] = Query(None)):
    """Get all budgets with computed spending stats."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    queryset = Budget.objects.filter(**filters)

    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-priority_level_int")

    budgets = queryset.annotate(
        monthly_spent=Coalesce(
            Sum(
                "transaction__amount",
                filter=Q(
                    transaction__date__gte=month_start,
                    transaction__active=True,
                    transaction__transaction_type="EXPENSE",
                ),
            ),
            0,
            output_field=DecimalField(),
        ),
        monthly_count=Count(
            "transaction__id",
            filter=Q(
                transaction__date__gte=month_start,
                transaction__active=True,
                transaction__transaction_type="EXPENSE",
            ),
        ),
    )

    result = [
        _compute_budget_stats(b, b.monthly_spent, b.monthly_count) for b in budgets
    ]
    return success_response(result)


@router.get("/budgets/{budget_id}/stats", response=BudgetStatsResponse)
def get_single_budget_stats(request, budget_id: int):
    """Get a single budget with computed spending stats."""
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    budget = (
        Budget.objects.filter(id=budget_id, user_id=request.user.id)
        .annotate(
            monthly_spent=Coalesce(
                Sum(
                    "transaction__amount",
                    filter=Q(
                        transaction__date__gte=month_start,
                        transaction__active=True,
                        transaction__transaction_type="EXPENSE",
                    ),
                ),
                0,
                output_field=DecimalField(),
            ),
            monthly_count=Count(
                "transaction__id",
                filter=Q(
                    transaction__date__gte=month_start,
                    transaction__active=True,
                    transaction__transaction_type="EXPENSE",
                ),
            ),
        )
        .first()
    )

    if not budget:
        return error_response("Budget not found", code=404)

    return success_response(
        _compute_budget_stats(budget, budget.monthly_spent, budget.monthly_count)
    )


# =============================================================================
# Goal Analytics
# =============================================================================


def _compute_goal_stats(goal) -> dict:
    """Compute derived fields for a goal object."""
    target = float(goal.target) if goal.target else 0.0
    saved = float(goal.saved_amount) if goal.saved_amount else 0.0
    progress = (saved / target * 100) if target > 0 else 0.0

    days_remaining = None
    if goal.due_date:
        today = timezone.localdate()
        delta = (goal.due_date - today).days
        days_remaining = max(0, delta)

    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "goal_name": goal.goal_name,
        "description": goal.description,
        "target": target,
        "saved_amount": saved,
        "start_date": goal.start_date,
        "due_date": goal.due_date,
        "icon": goal.icon,
        "color": goal.color,
        "plan": goal.plan,
        "active": goal.active,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
        # Computed
        "progress_percentage": round(progress, 1),
        "days_remaining": days_remaining,
    }


@router.get("/goals/stats", response=GoalStatsListResponse)
def get_goal_stats(request, active: Optional[bool] = Query(None)):
    """Get all goals with computed progress stats."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Goal.objects.filter(**filters)

    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-created_at")

    result = [_compute_goal_stats(g) for g in queryset]
    return success_response(result)


@router.get("/goals/{goal_id}/stats", response=GoalStatsResponse)
def get_single_goal_stats(request, goal_id: int):
    """Get a single goal with computed progress stats."""
    goal = Goal.objects.filter(id=goal_id, user_id=request.user.id).first()

    if not goal:
        return error_response("Goal not found", code=404)

    return success_response(_compute_goal_stats(goal))


# =============================================================================
# Transaction Analytics
# =============================================================================


@router.get("/transactions/summary", response=TransactionSummarySchema)
def get_transaction_summary(
    request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get total amount and count of transactions for a period."""
    filters = {
        "user_id": request.user.id,
        "active": True,
        "transaction_type": "EXPENSE",
    }

    if start_date:
        filters["date__gte"] = start_date
    if end_date:
        filters["date__lte"] = end_date

    agg = Transaction.objects.filter(**filters).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField()), count=Count("id")
    )

    return {
        "total_amount": float(agg["total"]),
        "currency": "EGP",
        "count": agg["count"],
    }


@router.get("/transactions/search", response=Dict[str, Any])
def search_transactions(
    request,
    query_text: Optional[str] = Query(None, alias="query"),
    category: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    neighbourhood: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Advanced transaction search."""
    queryset = Transaction.objects.filter(user_id=request.user.id, active=True)

    if query_text:
        queryset = queryset.filter(
            Q(description__icontains=query_text)
            | Q(budget__budget_name__icontains=query_text)
        )

    if category:
        queryset = queryset.filter(Q(budget__budget_name__icontains=category))

    if min_amount is not None:
        queryset = queryset.filter(amount__gte=min_amount)

    if max_amount is not None:
        queryset = queryset.filter(amount__lte=max_amount)

    if start_date:
        queryset = queryset.filter(date__gte=start_date)

    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    if city:
        queryset = queryset.filter(city__icontains=city)

    if neighbourhood:
        queryset = queryset.filter(neighbourhood__icontains=neighbourhood)

    transactions = queryset.order_by("-date").values(
        "id",
        "date",
        "amount",
        "description",
        "budget__budget_name",
        "city",
        "neighbourhood",
        "account_id",
        "transaction_type",
    )[:limit]

    result = []
    for txn in transactions:
        result.append(
            {
                "id": txn["id"],
                "date": txn["date"],
                "amount": float(txn["amount"]),
                "description": txn.get("description"),
                "budget_name": txn.get("budget__budget_name"),
                "city": txn.get("city"),
                "neighbourhood": txn.get("neighbourhood"),
                "account_id": txn.get("account_id"),
                "transaction_type": txn.get("transaction_type"),
            }
        )

    return {"status": "success", "message": "", "data": result, "count": len(result)}


# =============================================================================
# Existing Analytics (unchanged)
# =============================================================================


@router.get("/monthly-spend", response=Dict[str, Any])
def get_monthly_spend(request):
    """Aggregate spending by user's budgets for the current month."""
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    rows = (
        Transaction.objects.filter(
            user_id=request.user.id, date__gte=current_month_start
        )
        .select_related("budget")
        .values("budget__budget_name")
        .annotate(
            month=TruncMonth("date"),
            total_spent=Coalesce(Sum("amount"), 0, output_field=DecimalField()),
        )
        .order_by("-total_spent")
    )

    data = [
        {
            "budget_name": r["budget__budget_name"],
            "month": r["month"],
            "total_spent": float(r["total_spent"]),
        }
        for r in rows
    ]

    return {"data": data}


@router.get("/overspend", response=OverspendResponseSchema)
def get_overspend(request):
    """Identify categories where spending exceeds the budget limit."""
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    budgets = (
        Budget.objects.filter(user_id=request.user.id, active=True)
        .annotate(
            spent=Coalesce(
                Sum(
                    "transaction__amount",
                    filter=Q(transaction__date__gte=current_month_start),
                ),
                0,
                output_field=DecimalField(),
            )
        )
        .values("budget_name", "spent", "total_limit")
    )

    overspend_data = []
    total_spent_all = 0.0

    for r in budgets:
        spent = float(r["spent"])
        limit = float(r["total_limit"])
        total_spent_all += spent

        pct = (spent / limit * 100) if limit > 0 else 0
        row_data = {
            "budget_name": r["budget_name"],
            "spent": spent,
            "total_limit": limit,
            "pct_of_limit": round(pct, 2),
            "is_overspent": pct > 100,
        }
        overspend_data.append(row_data)

    income_total = Income.objects.filter(user_id=request.user.id).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField())
    )["total"]
    total_income = float(income_total) if income_total else 0.0

    accounts = Account.objects.filter(user_id=request.user.id, active=True)

    total_assets = 0.0
    total_liabilities = 0.0
    total_regular = 0.0
    total_savings = 0.0
    account_breakdown = []

    for acc in accounts:
        bal = float(acc.balance)
        account_breakdown.append(
            {"id": acc.id, "name": acc.name, "type": acc.type, "balance": bal}
        )

        if acc.type == Account.AccountType.SAVINGS:
            total_savings += bal
        else:
            total_regular += bal

        if bal >= 0:
            total_assets += bal
        else:
            total_liabilities += abs(bal)

    net_worth = total_assets - total_liabilities

    summary = {
        "total_income": total_income,
        "total_spent": total_spent_all,
        "net_position": net_worth,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_regular": total_regular,
        "total_savings": total_savings,
        "is_deficit": (total_spent_all > total_income),
        "accounts": account_breakdown,
    }

    return {"data": overspend_data, "summary": summary}


@router.get("/income-total", response=Dict[str, Any])
def get_total_income(request):
    """Aggregate active income items by type."""
    rows = (
        Income.objects.filter(user_id=request.user.id)
        .values("type_income")
        .annotate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))
        .order_by("-total")
    )

    data = [{"type_income": r["type_income"], "total": float(r["total"])} for r in rows]

    return {"data": data}


@router.get("/monthly-breakdown", response=MonthlyBreakdownSchema)
def get_monthly_breakdown(request, month: str = None):
    """Get detailed breakdown for a specific month."""
    user_id = request.user.id

    if month:
        try:
            target_date = timezone.datetime.strptime(month, "%Y-%m-%d").date()
            start_date = target_date.replace(day=1)
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD")
    else:
        start_date = timezone.now().date().replace(day=1)

    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1)

    income_agg = Income.objects.filter(user_id=user_id, active=True).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField())
    )
    total_income = float(income_agg["total"])

    tx_filter = Q(
        user_id=user_id,
        active=True,
        transaction_type="EXPENSE",
        date__gte=start_date,
        date__lt=end_date,
    )

    tx_stats = Transaction.objects.filter(tx_filter).aggregate(
        total_spent=Coalesce(Sum("amount"), 0, output_field=DecimalField()),
        count=Count("id"),
    )

    total_spent = float(tx_stats["total_spent"])
    transaction_count = tx_stats["count"]

    category_rows = (
        Transaction.objects.filter(tx_filter)
        .values("budget__budget_name", "budget__icon", "budget__color")
        .annotate(
            cat_total=Coalesce(Sum("amount"), 0, output_field=DecimalField()),
            cat_count=Count("id"),
        )
        .order_by("-cat_total")
    )

    categories = []
    for row in category_rows:
        amount = float(row["cat_total"])
        if row["budget__budget_name"]:
            name = row["budget__budget_name"]
            color = row["budget__color"]
            icon = row["budget__icon"]
        else:
            name = "Unbudgeted"
            color = "#9ca3af"
            icon = "help-circle-outline"

        pct = (amount / total_spent * 100) if total_spent > 0 else 0.0

        categories.append(
            {
                "name": name,
                "amount": amount,
                "count": row["cat_count"],
                "percentage": round(pct, 1),
                "color": color,
                "icon": icon,
            }
        )

    net_savings = total_income - total_spent
    avg_txn = (total_spent / transaction_count) if transaction_count > 0 else 0.0

    return {
        "total_income": total_income,
        "total_spent": total_spent,
        "net_savings": net_savings,
        "surplus": net_savings >= 0,
        "transaction_count": transaction_count,
        "avg_per_transaction": round(avg_txn, 2),
        "categories": categories,
    }

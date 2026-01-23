"""Analytics and administration database operations."""

import logging
from typing import Any, Dict

from ninja import Router
from django.db.models import Sum, DecimalField, Count, Q
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

# from core.utils.database import run_select, execute_modify, safe_json_body
from core.models import Transaction, Budget, Income

from features.auth.api import AuthBearer
from core.utils.responses import error_response
from .schemas import MonthlyBreakdownSchema, OverspendResponseSchema

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


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

    # Format to match original response structure
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

    # 1. Spend vs Limit per budget - using Django ORM
    from django.db.models import Q

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
        }

        if pct > 100:
            row_data["is_overspent"] = True
        else:
            row_data["is_overspent"] = False

        overspend_data.append(row_data)

    # 2. Total Income (Legacy metric, kept for reference)
    income_total = Income.objects.filter(user_id=request.user.id).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField())
    )["total"]
    total_income = float(income_total) if income_total else 0.0

    # 3. Account Balances (Real Net Worth)
    from core.models import Account

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

        # Break down by type
        if acc.type == Account.AccountType.SAVINGS:
            total_savings += bal
        else:
            # Regular accounts (Spendable Cash)
            total_regular += bal

        # All accounts are assets in this simplified model
        if bal >= 0:
            total_assets += bal
        else:
            # Overdraft
            total_liabilities += abs(bal)

    net_worth = total_assets - total_liabilities

    summary = {
        "total_income": total_income,
        "total_spent": total_spent_all,
        "net_position": net_worth,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_regular": total_regular,  # Spendable
        "total_savings": total_savings,  # Reserved
        "is_deficit": (total_spent_all > total_income),
        "accounts": account_breakdown,
    }

    summary = {
        "total_income": total_income,
        "total_spent": total_spent_all,
        "net_position": net_worth,  # Now reflects Real Net Worth
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "is_deficit": (total_spent_all > total_income),  # Keep monthly flow logic
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
    """
    Get detailed breakdown for a specific month.
    Query Param: month (YYYY-MM-DD), defaults to current month.
    """
    user_id = request.user.id

    # Date Range Calculation
    if month:
        try:
            target_date = timezone.datetime.strptime(month, "%Y-%m-%d").date()
            start_date = target_date.replace(day=1)
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD")
    else:
        start_date = timezone.now().date().replace(day=1)

    # Calculate end_date (start of next month)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1)

    # 1. Total Income (Recurring Model - Active items)
    # We sum all active income sources as they are monthly recurring
    income_agg = Income.objects.filter(user_id=user_id, active=True).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField())
    )
    total_income = float(income_agg["total"])

    # 2. Transactions (Expenses only)
    tx_filter = Q(
        user_id=user_id,
        active=True,
        transaction_type="EXPENSE",
        date__gte=start_date,
        date__lt=end_date,
    )

    # Aggregate Totals
    tx_stats = Transaction.objects.filter(tx_filter).aggregate(
        total_spent=Coalesce(Sum("amount"), 0, output_field=DecimalField()),
        count=Count("id"),
    )

    total_spent = float(tx_stats["total_spent"])
    transaction_count = tx_stats["count"]

    # 3. Category Breakdown (Group by Budget)
    # Group by budget to get the color/icon from budget description
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
        # Handle unbudgeted transactions
        if row["budget__budget_name"]:
            name = row["budget__budget_name"]
            color = row["budget__color"]
            icon = row["budget__icon"]
        else:
            name = "Unbudgeted"
            color = "#9ca3af"  # Gray
            icon = "help-circle-outline"  # or similar

        # Percentage
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

    # 5. Construct Flat Response (matching frontend interface)
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
        # "period": {"start": start_date, "end": end_date} # Optional, can be removed if strict
    }


# ============================================================================
# Admin/Debug endpoints - kept as raw SQL intentionally
# ============================================================================


# @router.post("/execute/select", response=Dict[str, Any])
# def execute_select_query(request):
#     """
#     Safe(-ish) endpoint for read-only SQL queries.
#     Expects JSON: {"query": "SELECT ...", "params": [...]}
#     """
#     body = safe_json_body(request)
#     raw_query = body.get("query", "").strip()
#     params = body.get("params", [])
#     limit = body.get("limit", 100)

#     if not raw_query:
#         return {"error": "No query provided"}

#     # Basic keyword check
#     lower_q = raw_query.lower()
#     if not lower_q.startswith("select") and not lower_q.startswith("with"):
#         return {"error": "Only SELECT or CTE queries allowed"}
#     if ";" in raw_query:
#         return {"error": "Multiple statements not allowed"}

#     # Force LIMIT if not present
#     if "limit" not in lower_q:
#         raw_query += f" LIMIT {int(limit)}"

#     rows = run_select(raw_query, params, log_name="execute_select")
#     return {"data": rows}


# @router.post("/execute/modify", response=Dict[str, Any])
# def execute_modify_query(request):
#     """
#     Endpoint for INSERT/UPDATE/DELETE queries.
#     Expects JSON: {"query": "INSERT ...", "params": [...]}
#     """
#     body = safe_json_body(request)
#     raw_query = body.get("query", "").strip()
#     params = body.get("params", [])

#     if not raw_query:
#         return {"error": "No query provided"}

#     rows_affected = execute_modify(raw_query, params, log_name="execute_modify")
#     return {"success": True, "rows_affected": rows_affected}

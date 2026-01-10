"""Analytics and administration database operations."""

import logging
from typing import Any, Dict

from ninja import Router
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

# from core.utils.database import run_select, execute_modify, safe_json_body
from core.models import Transaction, Budget, Income

from features.auth.api import AuthBearer

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


@router.get("/overspend", response=Dict[str, Any])
def get_overspend(request):
    """Identify categories where spending exceeds the budget limit."""
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # 1. Spend vs Limit per budget - using Django ORM
    from django.db.models import Q

    budgets = (
        Budget.objects.filter(user_id=request.user.id, is_active=True)
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

    # 2. Total Income
    income_total = Income.objects.filter(user_id=request.user.id).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField())
    )["total"]
    total_income = float(income_total) if income_total else 0.0

    summary = {
        "total_income": total_income,
        "total_spent": total_spent_all,
        "net_position": total_income - total_spent_all,
        "is_deficit": (total_spent_all > total_income),
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

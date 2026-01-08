"""Analytics and administration database operations."""
import logging
from typing import Any, Dict, List

from ninja import Router, Query
from django.db import connection

from ..core.database import run_select, run_select_single, execute_modify, safe_json_body

logger = logging.getLogger(__name__)
router = Router()


@router.get("/monthly-spend", response=Dict[str, Any])
def get_monthly_spend(request, user_id: int = Query(...)):
    """Aggregate spending by user's budgets for the current month."""
    query = """
       SELECT
           b.budget_name,
           DATE_TRUNC('month', t.date) as month,
           SUM(t.amount) as total_spent
       FROM transactions t
       JOIN budget b ON t.budget_id = b.budget_id
       WHERE t.user_id = %s
         AND t.date >= DATE_TRUNC('month', CURRENT_DATE)
       GROUP BY b.budget_name, DATE_TRUNC('month', t.date)
       ORDER BY total_spent DESC
    """
    rows = run_select(query, [user_id], log_name="monthly_spend")
    return {"data": rows}


@router.get("/overspend", response=Dict[str, Any])
def get_overspend(request, user_id: int = Query(...)):
    """Identify categories where spending exceeds the budget limit."""
    # 1. Spend vs Limit per budget
    query_budgets = """
        SELECT
            b.budget_name,
            COALESCE(SUM(t.amount), 0) as spent,
            b.total_limit
        FROM budget b
        LEFT JOIN transactions t
          ON b.budget_id = t.budget_id
          AND t.date >= DATE_TRUNC('month', CURRENT_DATE)
        WHERE b.user_id = %s AND b.is_active = true
        GROUP BY b.budget_id
    """
    rows = run_select(query_budgets, [user_id], log_name="overspend_budgets")
    
    overspend_data = []
    total_spent_all = 0.0
    
    for r in rows:
        spent = float(r["spent"])
        limit = float(r["total_limit"])
        total_spent_all += spent
        
        pct = (spent / limit * 100) if limit > 0 else 0
        r["pct_of_limit"] = round(pct, 2)
        r["spent"] = spent
        r["total_limit"] = limit
        
        if pct > 100:
            overspend_data.append(r)
            
    # 2. Total Income
    query_income = "SELECT SUM(amount) FROM income WHERE user_id = %s"
    row_inc = run_select_single(query_income, [user_id], log_name="overspend_income")
    total_income = float(row_inc["sum"]) if row_inc and row_inc["sum"] else 0.0
    
    summary = {
        "total_income": total_income,
        "total_spent": total_spent_all,
        "net_position": total_income - total_spent_all,
        "is_deficit": (total_spent_all > total_income)
    }
    
    return {"data": overspend_data, "summary": summary}


@router.get("/income-total", response=Dict[str, Any])
def get_total_income(request, user_id: int = Query(...)):
    """Aggregate active income items by type."""
    query = """
        SELECT type_income, SUM(amount) as total
        FROM income
        WHERE user_id = %s
        GROUP BY type_income
        ORDER BY total DESC
    """
    rows = run_select(query, [user_id], log_name="income_total")
    return {"data": rows}


@router.post("/execute/select", response=Dict[str, Any])
def execute_select_query(request):
    """
    Safe(-ish) endpoint for read-only SQL queries.
    Expects JSON: {"query": "SELECT ...", "params": [...]}
    """
    body = safe_json_body(request)
    raw_query = body.get("query", "").strip()
    params = body.get("params", [])
    limit = body.get("limit", 100)

    if not raw_query:
        return {"error": "No query provided"}
    
    # Basic keyword check
    lower_q = raw_query.lower()
    if not lower_q.startswith("select") and not lower_q.startswith("with"):
        return {"error": "Only SELECT or CTE queries allowed"}
    if ";" in raw_query:
        return {"error": "Multiple statements not allowed"}

    # Force LIMIT if not present
    if "limit" not in lower_q:
        raw_query += f" LIMIT {int(limit)}"

    rows = run_select(raw_query, params, log_name="execute_select")
    return {"data": rows}


@router.post("/execute/modify", response=Dict[str, Any])
def execute_modify_query(request):
    """
    Endpoint for INSERT/UPDATE/DELETE queries.
    Expects JSON: {"query": "INSERT ...", "params": [...]}
    """
    body = safe_json_body(request)
    raw_query = body.get("query", "").strip()
    params = body.get("params", [])

    if not raw_query:
        return {"error": "No query provided"}

    rows_affected = execute_modify(raw_query, params, log_name="execute_modify")
    return {"success": True, "rows_affected": rows_affected}

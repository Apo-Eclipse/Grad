"""Analytics database endpoints."""
import logging
from decimal import Decimal
from typing import Any, Dict, List
from ninja import Router, Query, Schema
from personal_assistant_api.core.database import (
    run_select,
    execute_modify_returning,
    safe_json_body,
    serialize_decimals,
)
from personal_assistant_api.core.responses import success_response

logger = logging.getLogger(__name__)
router = Router()


def _decimal_to_float(value: Any) -> float:
    """Convert Decimal-compatible values to floats for JSON serialization."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class SQLQuerySchema(Schema):
    query: str


@router.get("/monthly-spend", response=Dict[str, Any])
def get_monthly_spend(request, user_id: int = Query(...)):
    """Get monthly spending by budget."""
    query = """
        SELECT
            b.budget_name,
            DATE_TRUNC('month', t.date) AS month,
            ROUND(SUM(t.amount)::numeric, 2) AS total_spent
        FROM transactions t
        JOIN budget b ON t.budget_id = b.budget_id
        WHERE t.user_id = %s
        GROUP BY b.budget_name, month
        ORDER BY month DESC
    """
    rows = run_select(query, [user_id])
    return {"data": serialize_decimals(rows)}


@router.get("/overspend", response=Dict[str, Any])
def get_overspend(request, user_id: int = Query(...)):
    """Get budgets that are overspent this month along with income summary."""
    category_query = """
        SELECT
            b.budget_name,
            ROUND(SUM(t.amount)::numeric, 2) AS spent,
            b.total_limit,
            ROUND(100.0 * SUM(t.amount) / NULLIF(b.total_limit, 0), 2) AS pct_of_limit
        FROM transactions t
        JOIN budget b ON t.budget_id = b.budget_id
        WHERE t.user_id = %s
          AND DATE_TRUNC('month', t.date) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY b.budget_name, b.total_limit
        ORDER BY pct_of_limit DESC
    """
    categories = run_select(category_query, [user_id])

    income_rows = run_select(
        """
            SELECT COALESCE(SUM(amount), 0) AS total_income
            FROM income
            WHERE user_id = %s
        """,
        [user_id],
    )
    income_row = income_rows[0] if income_rows else {"total_income": Decimal("0")}

    total_spent = sum((_decimal_to_float(row.get("spent"))) for row in categories)
    total_income = _decimal_to_float(income_row.get("total_income"))

    summary = {
        "total_income": total_income,
        "total_spent": total_spent,
        "net_position": total_income - total_spent,
    }

    return {"data": serialize_decimals(categories), "summary": summary}


@router.get("/income-total", response=Dict[str, Any])
def get_total_income(request, user_id: int = Query(...)):
    """Get total income by type."""
    query = """
        SELECT
            type_income,
            ROUND(SUM(amount)::numeric, 2) AS total_amount
        FROM income
        WHERE user_id = %s
        GROUP BY type_income
        ORDER BY total_amount DESC
    """
    rows = run_select(query, [user_id])
    return {"data": serialize_decimals(rows)}


@router.get("/spending_by_category", response=List[Dict[str, Any]])
def spending_by_category(request, user_id: int):
    """Get spending grouped by category."""
    sql = """
        SELECT type_spending, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = %s 
        GROUP BY type_spending
    """
    return serialize_decimals(run_select(sql, [user_id]))


@router.get("/monthly_spending", response=List[Dict[str, Any]])
def monthly_spending(request, user_id: int):
    """Get monthly spending totals."""
    sql = """
        SELECT DATE_TRUNC('month', date) as month, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = %s 
        GROUP BY month 
        ORDER BY month DESC
    """
    return serialize_decimals(run_select(sql, [user_id]))


@router.post("/execute/select", response=Dict[str, Any])
def execute_select_query(request):
    """Execute a SELECT query (read-only)."""
    body = safe_json_body(request)
    query = (body.get("query") or "").strip()

    if not query:
        return {"success": False, "error": "Query is required", "data": []}

    params = list(body.get("params") or [])
    limit = body.get("limit", 100)
    try:
        limit_value = int(limit)
    except (TypeError, ValueError):
        limit_value = 100
    limit_value = max(1, min(limit_value, 1000))

    query_upper = query.lstrip().upper()
    if not query_upper.startswith(("SELECT", "WITH")):
        return {
            "success": False,
            "error": "Only SELECT queries are allowed for retrieval. Query must start with SELECT or WITH.",
            "data": [],
        }

    if "LIMIT" not in query_upper:
        query = query.rstrip(";").strip() + " LIMIT %s"
        params.append(limit_value)

    try:
        results = run_select(query, params)
        return {
            "success": True,
            "count": len(results),
            "data": serialize_decimals(results),
        }
    except Exception as exc:
        logger.exception("Error executing custom SELECT")
        return {
            "success": False,
            "error": str(exc),
            "data": [],
        }


@router.post("/execute/modify", response=Dict[str, Any])
def execute_modify_query(request):
    """Execute INSERT, UPDATE, or DELETE query (write operations)."""
    body = safe_json_body(request)
    query = (body.get("query") or "").strip()

    if not query:
        return {
            "success": False,
            "error": "Query is required",
            "rows_affected": 0,
        }

    params = list(body.get("params") or [])
    query_upper = query.lstrip().upper()
    if not query_upper.startswith(("INSERT", "UPDATE", "DELETE")):
        return {
            "success": False,
            "error": "Only INSERT, UPDATE, and DELETE queries are allowed for modification",
            "rows_affected": 0,
        }

    success, rows_affected, _ = execute_modify_returning(query, params, log_name="custom_modify")
    if not success:
        return {
            "success": False,
            "error": "Failed to execute query",
            "rows_affected": 0,
        }

    return {
        "success": True,
        "rows_affected": rows_affected,
        "message": f"Query executed successfully. {rows_affected} row(s) affected.",
    }


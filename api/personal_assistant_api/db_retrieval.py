"""Database retrieval endpoints using Django ORM."""
import json
import logging
from typing import Any, Dict, List, Optional

from django.db import connection
from ninja import Query, Router

logger = logging.getLogger(__name__)
db_router = Router()


def dictfetchall(cursor):
    """Convert database cursor results to list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _run_select(
    query: str,
    params: Optional[List[Any]] = None,
    *,
    single: bool = False,
    default: Optional[Any] = None,
    log_name: str = "query",
):
    """Execute a read-only query and return dict rows."""
    params = list(params or [])
    fallback = default if default is not None else ({} if single else [])
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = dictfetchall(cursor)
            return rows[0] if single else rows
    except Exception:
        logger.exception("Error executing %s", log_name)
        return fallback


def _data_response(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap rows in the {'data': rows} envelope used by analytics endpoints."""
    return {"data": rows}


def _safe_json_body(request) -> Dict[str, Any]:
    """Parse JSON request body safely."""
    try:
        raw = request.body or b"{}"
        return json.loads(raw)
    except Exception:
        logger.debug("Received invalid JSON body", exc_info=True)
        return {}


# ============ TRANSACTIONS ============
@db_router.get("transactions", response=List[Dict[str, Any]])
def get_transactions(
    request,
    user_id: int = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve transactions for a user."""
    query = """
        SELECT
            transaction_id,
            date,
            amount,
            time,
            store_name,
            city,
            type_spending,
            user_id,
            budget_id,
            neighbourhood,
            created_at
        FROM transactions
        WHERE user_id = %s
    """
    params: List[Any] = [user_id]

    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    query += " ORDER BY date DESC LIMIT %s"
    params.append(limit)

    return _run_select(query, params, log_name="transactions")


# ============ BUDGET ============
@db_router.get("budget", response=List[Dict[str, Any]])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve all budgets for a user."""
    query = """
        SELECT
            budget_id,
            user_id,
            budget_name,
            description,
            total_limit,
            priority_level_int,
            is_active,
            created_at,
            updated_at
        FROM budget
        WHERE user_id = %s
        ORDER BY priority_level_int DESC
    """
    return _run_select(query, [user_id], log_name="budgets")


# ============ USERS ============
@db_router.get("users/{user_id}", response=Dict[str, Any])
def get_user(request, user_id: int):
    """Retrieve a specific user by ID."""
    query = """
        SELECT
            user_id,
            first_name,
            last_name,
            job_title,
            address,
            birthday,
            gender,
            employment_status,
            education_level,
            created_at,
            updated_at
        FROM users
        WHERE user_id = %s
    """
    return _run_select(query, [user_id], single=True, default={}, log_name="user")


# ============ INCOME ============
@db_router.get("income", response=List[Dict[str, Any]])
def get_income(request, user_id: int = Query(...)):
    """Retrieve all income sources for a user."""
    query = """
        SELECT
            income_id,
            user_id,
            type_income,
            amount,
            period,
            description,
            created_at,
            updated_at
        FROM income
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    return _run_select(query, [user_id], log_name="income")


# ============ GOALS ============
@db_router.get("goals", response=List[Dict[str, Any]])
def get_goals(request, user_id: int = Query(...), status: Optional[str] = Query(None)):
    """Retrieve goals for a user."""
    query = """
        SELECT
            goal_id,
            user_id,
            goal_name,
            description,
            target,
            start_date,
            due_date,
            status,
            created_at,
            updated_at
        FROM goals
        WHERE user_id = %s
    """
    params: List[Any] = [user_id]

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY due_date ASC"
    return _run_select(query, params, log_name="goals")


# ============ CHAT CONVERSATIONS ============
@db_router.get("conversations", response=List[Dict[str, Any]])
def get_conversations(request, user_id: int = Query(...), limit: int = Query(50, le=500)):
    """Retrieve chat conversations for a user."""
    query = """
        SELECT
            conversation_id,
            user_id,
            title,
            channel,
            started_at,
            last_message_at,
            summary_text,
            summary_created_at
        FROM chat_conversations
        WHERE user_id = %s
        ORDER BY last_message_at DESC
        LIMIT %s
    """
    return _run_select(query, [user_id, limit], log_name="conversations")


# ============ CHAT MESSAGES ============
@db_router.get("messages", response=List[Dict[str, Any]])
def get_messages(request, conversation_id: int = Query(...), limit: int = Query(100, le=1000)):
    """Retrieve messages from a conversation."""
    query = """
        SELECT
            message_id,
            conversation_id,
            sender_type,
            source_agent,
            content,
            content_type,
            language,
            created_at
        FROM chat_messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return _run_select(query, [conversation_id, limit], log_name="messages")


# ============ ANALYTICS ============
@db_router.get("analytics/monthly-spend", response=Dict[str, Any])
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
    rows = _run_select(query, [user_id], log_name="monthly_spend")
    return _data_response(rows)


@db_router.get("analytics/overspend", response=Dict[str, Any])
def get_overspend(request, user_id: int = Query(...)):
    """Get budgets that are overspent this month."""
    query = """
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
    rows = _run_select(query, [user_id], log_name="overspend")
    return _data_response(rows)


@db_router.get("analytics/income-total", response=Dict[str, Any])
def get_total_income(request, user_id: int = Query(...)):
    """Get total income by type."""
    query = """
        SELECT
            type_income,
            period,
            ROUND(SUM(amount)::numeric, 2) AS total_amount
        FROM income
        WHERE user_id = %s
        GROUP BY type_income, period
        ORDER BY total_amount DESC
    """
    rows = _run_select(query, [user_id], log_name="income_total")
    return _data_response(rows)


# ============ EXECUTE CUSTOM SQL QUERIES ============
@db_router.post("execute/select", response=Dict[str, Any])
def execute_select_query(request):
    """
    Execute a SELECT query (read-only).

    Request body:
    {
        "query": "SELECT * FROM transactions WHERE user_id = %s",
        "params": [1],
        "limit": 100
    }
    """
    body = _safe_json_body(request)
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
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = dictfetchall(cursor)
        return {
            "success": True,
            "count": len(results),
            "data": results,
        }
    except Exception as exc:
        logger.exception("Error executing custom SELECT")
        return {
            "success": False,
            "error": str(exc),
            "data": [],
        }


@db_router.post("execute/modify", response=Dict[str, Any])
def execute_modify_query(request):
    """
    Execute INSERT, UPDATE, or DELETE query (write operations).

    Request body:
    {
        "query": "UPDATE transactions SET amount = %s WHERE transaction_id = %s",
        "params": [100.50, 123]
    }
    """
    body = _safe_json_body(request)
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

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
        connection.commit()
        return {
            "success": True,
            "rows_affected": rows_affected,
            "message": f"Query executed successfully. {rows_affected} row(s) affected.",
        }
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            logger.debug("Rollback failed after modify query", exc_info=True)
        logger.exception("Error executing modify query")
        return {
            "success": False,
            "error": str(exc),
            "rows_affected": 0,
        }

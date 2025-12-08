"""Database retrieval endpoints using Django ORM."""
import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import connection
from ninja import Query, Router

from .schemas import (
    BudgetCreateSchema,
    BudgetUpdateSchema,
    GoalCreateSchema,
    IncomeCreateSchema,
    TransactionCreateSchema,
    TransactionUpdateSchema,
    UserCreateSchema,
)

logger = logging.getLogger(__name__)
db_router = Router()


def dictfetchall(cursor):
    """Convert database cursor results to list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dictfetchone(cursor):
    """Convert the next row from the cursor to a dict."""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


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
            if single:
                return rows[0] if rows else fallback
            return rows
    except Exception:
        logger.exception("Error executing %s", log_name)
        return fallback


def _execute_modify(
    query: str,
    params: List[Any],
    *,
    log_name: str,
) -> Tuple[bool, int, Optional[Dict[str, Any]]]:
    """Execute a write query and return (success, rows_affected, returned_row)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = dictfetchone(cursor) if cursor.description else None
            rows_affected = cursor.rowcount
        connection.commit()
        return True, rows_affected, row
    except Exception:
        try:
            connection.rollback()
        except Exception:
            logger.debug("Rollback failed after %s", log_name, exc_info=True)
        logger.exception("Error executing %s", log_name)
        return False, 0, None


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
            t.transaction_id,
            t.user_id,
            t.date,
            t.amount,
            t.time,
            t.store_name,
            t.city,
            t.type_spending,
            t.budget_id,
            b.budget_name,
            t.neighbourhood,
            t.created_at
        FROM transactions t
        LEFT JOIN budget b ON t.budget_id = b.budget_id
        WHERE t.user_id = %s
    """
    params: List[Any] = [user_id]

    if start_date:
        query += " AND t.date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND t.date <= %s"
        params.append(end_date)

    query += " ORDER BY t.date DESC, t.time DESC NULLS LAST LIMIT %s"
    params.append(limit)

    return _run_select(query, params, log_name="transactions")


@db_router.post("transactions", response=Dict[str, Any])
def create_transaction(request, payload: TransactionCreateSchema):
    """Create a new transaction row."""
    query = """
        INSERT INTO transactions (
            user_id,
            date,
            amount,
            time,
            store_name,
            city,
            type_spending,
            budget_id,
            neighbourhood
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING
            transaction_id,
            user_id,
            date,
            amount,
            time,
            store_name,
            city,
            type_spending,
            budget_id,
            neighbourhood,
            created_at
    """
    # Time is already a string from the schema, pass it directly
    params = [
        payload.user_id,
        payload.date,
        payload.amount,
        payload.time,  # Already a string or None
        payload.store_name,
        payload.city,
        payload.type_spending,
        payload.budget_id,
        payload.neighbourhood,
    ]
    success, _, row = _execute_modify(query, params, log_name="create_transaction")
    if not success or row is None:
        return {"success": False, "error": "Failed to create transaction"}
    return {"success": True, "transaction": row}


@db_router.put("transactions/{transaction_id}", response=Dict[str, Any])
def update_transaction(request, transaction_id: int, payload: TransactionUpdateSchema):
    """Update an existing transaction."""
    updates = payload.dict(exclude_unset=True)
    set_clause = ", ".join(f"{field} = %s" for field in updates)
    params = list(updates.values()) + [transaction_id]

    query = f"""
        UPDATE transactions
        SET {set_clause}
        WHERE transaction_id = %s
        RETURNING
            transaction_id,
            user_id,
            date,
            amount,
            time,
            store_name,
            city,
            type_spending,
            budget_id,
            neighbourhood,
            created_at
    """

    success, rows_affected, row = _execute_modify(query, params, log_name="update_transaction")
    if not success:
        return {"success": False, "error": "Failed to update transaction"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Transaction not found"}
    return {"success": True, "transaction": row}


@db_router.delete("transactions/{transaction_id}", response=Dict[str, Any])
def delete_transaction(request, transaction_id: int):
    """Delete a transaction permanently."""
    query = """
        DELETE FROM transactions
        WHERE transaction_id = %s
        RETURNING transaction_id
    """
    success, rows_affected, row = _execute_modify(query, [transaction_id], log_name="delete_transaction")
    if not success:
        return {"success": False, "error": "Failed to delete transaction"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Transaction not found"}
    return {"success": True, "message": "Transaction deleted", "transaction_id": row["transaction_id"]}


@db_router.get("transactions/search", response=Dict[str, Any])
def search_transactions(
    request,
    user_id: int = Query(...),
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
    """Advanced transaction search with multiple filters."""
    sql_query = """
        SELECT
            t.transaction_id,
            t.user_id,
            t.date,
            t.amount,
            t.time,
            t.store_name,
            t.city,
            t.type_spending,
            t.budget_id,
            b.budget_name,
            t.neighbourhood,
            t.created_at
        FROM transactions t
        LEFT JOIN budget b ON t.budget_id = b.budget_id
        WHERE t.user_id = %s
    """
    params: List[Any] = [user_id]

    if query_text:
        sql_query += " AND (t.store_name ILIKE %s OR t.type_spending ILIKE %s)"
        search_term = f"%{query_text}%"
        params.extend([search_term, search_term])

    if category:
        sql_query += " AND (t.type_spending = %s OR b.budget_name ILIKE %s)"
        params.extend([category, f"%{category}%"])

    if min_amount is not None:
        sql_query += " AND t.amount >= %s"
        params.append(min_amount)

    if max_amount is not None:
        sql_query += " AND t.amount <= %s"
        params.append(max_amount)

    if start_date:
        sql_query += " AND t.date >= %s"
        params.append(start_date)

    if end_date:
        sql_query += " AND t.date <= %s"
        params.append(end_date)

    if city:
        sql_query += " AND t.city ILIKE %s"
        params.append(f"%{city}%")

    if neighbourhood:
        sql_query += " AND t.neighbourhood ILIKE %s"
        params.append(f"%{neighbourhood}%")

    sql_query += " ORDER BY t.date DESC, t.time DESC NULLS LAST LIMIT %s"
    params.append(limit)

    results = _run_select(sql_query, params, log_name="transaction_search")
    return {"success": True, "count": len(results), "transactions": results}


# ============ BUDGET ============
def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve active user budgets (reusable function)."""
    query = """
        SELECT
            budget_id,
            budget_name,
            description,
            total_limit,
            priority_level_int,
            is_active,
            created_at,
            updated_at
        FROM budget
        WHERE user_id = %s
          AND is_active = true
        ORDER BY priority_level_int ASC, budget_name
    """
    return _run_select(query, [user_id], log_name="budgets")


@db_router.get("budget", response=List[Dict[str, Any]])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve active user budgets only."""
    return fetch_active_budgets(user_id)


@db_router.post("budget", response=Dict[str, Any])
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    query = """
        INSERT INTO budget (
            user_id,
            budget_name,
            description,
            total_limit,
            priority_level_int,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING
            budget_id,
            user_id,
            budget_name,
            description,
            total_limit,
            priority_level_int,
            is_active,
            created_at,
            updated_at
    """
    params = [
        payload.user_id,
        payload.budget_name,
        payload.description,
        payload.total_limit,
        payload.priority_level_int,
        payload.is_active,
    ]
    success, _, row = _execute_modify(query, params, log_name="create_budget")
    if not success or row is None:
        return {"success": False, "error": "Failed to create budget"}
    return {"success": True, "budget": row}


@db_router.put("budget/{budget_id}", response=Dict[str, Any])
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    fields = payload.dict(exclude_unset=True)
    if not fields:
        return {"success": False, "error": "No fields provided for update"}

    set_clauses = [f"{k} = %s" for k in fields.keys()]
    params = list(fields.values())
    params.append(budget_id)

    query = f"""
        UPDATE budget
        SET {', '.join(set_clauses)}, updated_at = NOW()
        WHERE budget_id = %s
        RETURNING budget_id, budget_name, total_limit, priority_level_int, is_active, updated_at
    """

    success, _, row = _execute_modify(query, params, log_name="update_budget")
    if not success:
        return {"success": False, "error": "Failed to update budget"}
    if row is None:
         return {"success": False, "error": "Budget not found"}

    return {"success": True, "message": "Budget updated successfully", "budget": row}


@db_router.delete("budget/{budget_id}", response=Dict[str, Any])
def delete_budget(request, budget_id: int):
    """Soft delete a budget by setting is_active to false."""
    query = """
        UPDATE budget
        SET is_active = false, updated_at = NOW()
        WHERE budget_id = %s
        RETURNING budget_id, budget_name, is_active, updated_at
    """
    success, rows_affected, row = _execute_modify(query, [budget_id], log_name="delete_budget")
    if not success:
        return {"success": False, "error": "Failed to update budget"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Budget not found"}
    return {"success": True, "message": "Budget marked as inactive", "budget": row}


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


@db_router.get("users/{user_id}/exists", response=Dict[str, Any])
def check_user_exists(request, user_id: int):
    """Check if a user exists in the database."""
    query = """
        SELECT
            user_id,
            first_name,
            last_name
        FROM users
        WHERE user_id = %s
    """
    result = _run_select(query, [user_id], single=True, default={}, log_name="user_exists")
    if result and result.get("user_id") is not None:
        return {
            "exists": True,
            "user_id": result.get("user_id"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
        }
    return {"exists": False, "user_id": user_id}


@db_router.post("users", response=Dict[str, Any])
def create_user(request, payload: UserCreateSchema):
    """Create a new user with optional custom user_id."""
    if payload.user_id is not None:
        # Insert with custom user_id
        query = """
            INSERT INTO users (
                user_id, first_name, last_name, birthday, job_title, address,
                employment_status, education_level, gender
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING user_id, first_name, last_name, job_title, employment_status
        """
        params = [
            payload.user_id,
            payload.first_name,
            payload.last_name,
            payload.birthday,
            payload.job_title,
            payload.address,
            payload.employment_status,
            payload.education_level,
            payload.gender,
        ]
    else:
        # Auto-generate user_id
        query = """
            INSERT INTO users (
                first_name, last_name, birthday, job_title, address,
                employment_status, education_level, gender
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING user_id, first_name, last_name, job_title, employment_status
        """
        params = [
            payload.first_name,
            payload.last_name,
            payload.birthday,
            payload.job_title,
            payload.address,
            payload.employment_status,
            payload.education_level,
            payload.gender,
        ]
    success, _, row = _execute_modify(query, params, log_name="create_user")
    if not success or row is None:
        return {"success": False, "error": "Failed to create user"}
    return {"success": True, "message": "User created successfully", "user": row}


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
            description,
            created_at,
            updated_at
        FROM income
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    return _run_select(query, [user_id], log_name="income")


@db_router.get("income/active", response=List[Dict[str, Any]])
def get_active_income(request, user_id: int = Query(...)):
    """Retrieve all income sources for a user."""
    query = """
        SELECT
            income_id,
            user_id,
            type_income,
            amount,
            description,
            created_at,
            updated_at
        FROM income
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    return _run_select(query, [user_id], log_name="income_active")


@db_router.post("income", response=Dict[str, Any])
def create_income(request, payload: IncomeCreateSchema):
    """Add a new income source."""
    query = """
        INSERT INTO income (user_id, type_income, amount, description)
        VALUES (%s, %s, %s, %s)
        RETURNING income_id, user_id, type_income, amount, description
    """
    params = [
        payload.user_id,
        payload.type_income,
        payload.amount,
        payload.description,
    ]
    success, _, row = _execute_modify(query, params, log_name="create_income")
    if not success or row is None:
        return {"success": False, "error": "Failed to create income source"}
    return {"success": True, "message": "Income source created successfully", "income": row}


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


@db_router.post("goals", response=Dict[str, Any])
def create_goal(request, payload: GoalCreateSchema):
    """Create a new goal."""
    query = """
        INSERT INTO goals (
            user_id,
            goal_name,
            description,
            target,
            start_date,
            due_date,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING
            goal_id,
            user_id,
            goal_name,
            target,
            status,
            start_date,
            due_date,
            created_at,
            updated_at
    """
    params = [
        payload.user_id,
        payload.goal_name,
        payload.description,
        payload.target,
        payload.start_date,
        payload.due_date,
        payload.status,
    ]
    success, _, row = _execute_modify(query, params, log_name="create_goal")
    if not success or row is None:
        return {"success": False, "error": "Failed to create goal"}
    return {"success": True, "goal": row}


@db_router.delete("goals/{goal_id}", response=Dict[str, Any])
def delete_goal(request, goal_id: int):
    """Soft delete a goal by setting status to 'inactive'."""
    query = """
        UPDATE goals
        SET status = 'inactive', updated_at = NOW()
        WHERE goal_id = %s
        RETURNING goal_id, goal_name, status, updated_at
    """
    success, rows_affected, row = _execute_modify(query, [goal_id], log_name="delete_goal")
    if not success:
        return {"success": False, "error": "Failed to update goal"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Goal not found"}
    return {"success": True, "message": "Goal marked as inactive", "goal": row}


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
    categories = _run_select(category_query, [user_id], log_name="overspend_categories")

    income_row = _run_select(
        """
            SELECT COALESCE(SUM(amount), 0) AS total_income
            FROM income
            WHERE user_id = %s
        """,
        [user_id],
        single=True,
        default={"total_income": Decimal("0")},
        log_name="overspend_income",
    )

    total_spent = sum((row.get("spent") or Decimal("0")) for row in categories)
    total_income = income_row.get("total_income") if income_row else Decimal("0")

    summary = {
        "total_income": _decimal_to_float(total_income),
        "total_spent": _decimal_to_float(total_spent),
        "net_position": _decimal_to_float(total_income - total_spent),
    }

    return {"data": categories, "summary": summary}


@db_router.get("analytics/income-total", response=Dict[str, Any])
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
    rows = _run_select(query, [user_id], log_name="income_total")
    return _data_response(rows)


# ============ EXECUTE CUSTOM SQL QUERIES ============
@db_router.post("execute/select", response=Dict[str, Any])
def execute_select_query(request):
    """Execute a SELECT query (read-only)."""
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
    """Execute INSERT, UPDATE, or DELETE query (write operations)."""
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

    success, rows_affected, _ = _execute_modify(query, params, log_name="custom_modify")
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

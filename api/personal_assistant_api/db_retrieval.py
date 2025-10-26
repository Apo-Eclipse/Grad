"""Database retrieval endpoints using Django ORM."""
import logging
import json
from typing import Dict, Any, List, Optional
from ninja import Router, Query
from django.db import connection
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)
db_router = Router()


def dictfetchall(cursor):
    """Convert database cursor results to list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ============ TRANSACTIONS ============
@db_router.get("transactions", response=List[Dict[str, Any]])
def get_transactions(
    request,
    user_id: int = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """Retrieve transactions for a user."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT transaction_id, date, amount, time, store_name, city, type_spending, 
                   user_id, budget_id, neighbourhood, created_at
            FROM transactions
            WHERE user_id = %s
            """
            params = [user_id]
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            query += f" ORDER BY date DESC LIMIT {limit}"
            
            cursor.execute(query, params)
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return []


# ============ BUDGET ============
@db_router.get("budget", response=List[Dict[str, Any]])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve all budgets for a user."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT budget_id, user_id, budget_name, description, total_limit, 
                   priority_level_int, is_active, created_at, updated_at
            FROM budget
            WHERE user_id = %s
            ORDER BY priority_level_int DESC
            """
            cursor.execute(query, [user_id])
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching budgets: {e}")
        return []


# ============ USERS ============
@db_router.get("users/{user_id}", response=Dict[str, Any])
def get_user(request, user_id: int):
    """Retrieve a specific user by ID."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT user_id, first_name, last_name, job_title, address, birthday, 
                   gender, employment_status, education_level, created_at, updated_at
            FROM users
            WHERE user_id = %s
            """
            cursor.execute(query, [user_id])
            results = dictfetchall(cursor)
            return results[0] if results else {}
    
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return {}


# ============ INCOME ============
@db_router.get("income", response=List[Dict[str, Any]])
def get_income(request, user_id: int = Query(...)):
    """Retrieve all income sources for a user."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT income_id, user_id, type_income, amount, period, description, 
                   created_at, updated_at
            FROM income
            WHERE user_id = %s
            ORDER BY created_at DESC
            """
            cursor.execute(query, [user_id])
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching income: {e}")
        return []


# ============ GOALS ============
@db_router.get("goals", response=List[Dict[str, Any]])
def get_goals(request, user_id: int = Query(...), status: Optional[str] = Query(None)):
    """Retrieve goals for a user."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT goal_id, user_id, goal_name, description, target, start_date, 
                   due_date, status, created_at, updated_at
            FROM goals
            WHERE user_id = %s
            """
            params = [user_id]
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY due_date ASC"
            
            cursor.execute(query, params)
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching goals: {e}")
        return []


# ============ CHAT CONVERSATIONS ============
@db_router.get("conversations", response=List[Dict[str, Any]])
def get_conversations(request, user_id: int = Query(...), limit: int = Query(50, le=500)):
    """Retrieve chat conversations for a user."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT conversation_id, user_id, title, channel, started_at, last_message_at, 
                   summary_text, summary_created_at
            FROM chat_conversations
            WHERE user_id = %s
            ORDER BY last_message_at DESC
            LIMIT %s
            """
            cursor.execute(query, [user_id, limit])
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return []


# ============ CHAT MESSAGES ============
@db_router.get("messages", response=List[Dict[str, Any]])
def get_messages(request, conversation_id: int = Query(...), limit: int = Query(100, le=1000)):
    """Retrieve messages from a conversation."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT message_id, conversation_id, sender_type, source_agent, content, 
                   content_type, language, created_at
            FROM chat_messages
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """
            cursor.execute(query, [conversation_id, limit])
            return dictfetchall(cursor)
    
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


# ============ ANALYTICS ============
@db_router.get("analytics/monthly-spend", response=Dict[str, Any])
def get_monthly_spend(request, user_id: int = Query(...)):
    """Get monthly spending by budget."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT b.budget_name, DATE_TRUNC('month', t.date) AS month, 
                   ROUND(SUM(t.amount)::numeric, 2) AS total_spent
            FROM transactions t 
            JOIN budget b ON t.budget_id = b.budget_id
            WHERE t.user_id = %s
            GROUP BY b.budget_name, month
            ORDER BY month DESC
            """
            cursor.execute(query, [user_id])
            return {"data": dictfetchall(cursor)}
    
    except Exception as e:
        logger.error(f"Error fetching monthly spend: {e}")
        return {"data": []}


@db_router.get("analytics/overspend", response=Dict[str, Any])
def get_overspend(request, user_id: int = Query(...)):
    """Get budgets that are overspent this month."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT b.budget_name, ROUND(SUM(t.amount)::numeric, 2) AS spent, 
                   b.total_limit, ROUND(100.0 * SUM(t.amount) / NULLIF(b.total_limit, 0), 2) AS pct_of_limit
            FROM transactions t 
            JOIN budget b ON t.budget_id = b.budget_id
            WHERE t.user_id = %s 
              AND DATE_TRUNC('month', t.date) = DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY b.budget_name, b.total_limit
            ORDER BY pct_of_limit DESC
            """
            cursor.execute(query, [user_id])
            return {"data": dictfetchall(cursor)}
    
    except Exception as e:
        logger.error(f"Error fetching overspend: {e}")
        return {"data": []}


@db_router.get("analytics/income-total", response=Dict[str, Any])
def get_total_income(request, user_id: int = Query(...)):
    """Get total income by type."""
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT type_income, period, ROUND(SUM(amount)::numeric, 2) AS total_amount
            FROM income
            WHERE user_id = %s
            GROUP BY type_income, period
            ORDER BY total_amount DESC
            """
            cursor.execute(query, [user_id])
            return {"data": dictfetchall(cursor)}
    
    except Exception as e:
        logger.error(f"Error fetching income total: {e}")
        return {"data": []}


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
    try:
        # Parse JSON body
        try:
            body = json.loads(request.body)
        except Exception:
            body = {}
        
        query = body.get("query", "").strip()
        params = body.get("params", [])
        limit = body.get("limit", 100)
        
        # Security: Only allow SELECT queries
        # Check for SELECT in uppercase (after removing whitespace/newlines at start)
        query_upper = query.upper()
        # Handle WITH clauses, comments, etc.
        query_upper_stripped = query_upper.lstrip()
        
        # Check if it's a SELECT query (including CTEs with WITH ... SELECT)
        if not (query_upper_stripped.startswith("SELECT") or query_upper_stripped.startswith("WITH")):
            return {
                "error": f"Only SELECT queries are allowed for retrieval. Query must start with SELECT or WITH.",
                "data": []
            }
        
        # Add LIMIT if not present and it's safe to do so
        if "LIMIT" not in query_upper:
            # Remove trailing semicolon if present
            query = query.rstrip(";").strip()
            query += f" LIMIT {min(limit, 1000)}"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = dictfetchall(cursor)
            return {
                "success": True,
                "count": len(results),
                "data": results
            }
    
    except Exception as e:
        logger.error(f"Error executing SELECT query: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
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
    try:
        # Parse JSON body
        try:
            body = json.loads(request.body)
        except Exception:
            body = {}
        
        query = body.get("query", "").strip()
        params = body.get("params", [])
        
        # Security: Only allow INSERT, UPDATE, DELETE queries
        query_upper = query.upper()
        if not any(query_upper.startswith(op) for op in ["INSERT", "UPDATE", "DELETE"]):
            return {
                "success": False,
                "error": "Only INSERT, UPDATE, and DELETE queries are allowed for modification",
                "rows_affected": 0
            }
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
            connection.commit()
            
            return {
                "success": True,
                "rows_affected": rows_affected,
                "message": f"Query executed successfully. {rows_affected} row(s) affected."
            }
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Error executing modify query: {e}")
        return {
            "success": False,
            "error": str(e),
            "rows_affected": 0
        }

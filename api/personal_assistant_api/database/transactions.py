"""Transactions database operations."""
import logging
from typing import Any, Dict, List, Optional

from ninja import Router, Query

from ..core.database import run_select, execute_modify
from ..core.responses import success_response, error_response
from .schemas import TransactionCreateSchema, TransactionUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
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

    return run_select(query, params, log_name="transactions")


@router.post("/", response=Dict[str, Any])
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
    params = [
        payload.user_id,
        payload.date,
        payload.amount,
        payload.time,
        payload.store_name,
        payload.city,
        payload.type_spending,
        payload.budget_id,
        payload.neighbourhood,
    ]
    
    # We use run_select for INSERT...RETURNING as strict execute_modify returns rowcount
    # To keep consistent with requested structure using core.database utils:
    # We can use execute_modify_returning if available, or run_select (since it returns rows)
    # The user manual Step 1 asked for execute_modify_returning, let's use it if defined in core
    # (Checking my previous step: yes, I added execute_modify_returning in core/database.py)
    
    from ..core.database import execute_modify_returning
    
    success, _, row = execute_modify_returning(query, params, log_name="create_transaction")
    if not success or row is None:
        return error_response("Failed to create transaction")
    
    return success_response(row, "Transaction created successfully")


@router.get("/{transaction_id}", response=Dict[str, Any])
def get_transaction(request, transaction_id: int):
    """Get a single transaction."""
    from ..core.database import run_select_single
    
    query = """
        SELECT * FROM transactions WHERE transaction_id = %s
    """
    row = run_select_single(query, [transaction_id], log_name="get_transaction")
    if not row:
        return error_response("Transaction not found", code=404)
    return success_response(row)


@router.put("/{transaction_id}", response=Dict[str, Any])
def update_transaction(request, transaction_id: int, payload: TransactionUpdateSchema):
    """Update an existing transaction."""
    from ..core.database import execute_modify_returning

    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

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

    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_transaction")
    if not success:
        return error_response("Failed to update transaction")
    if rows_affected == 0 or row is None:
        return error_response("Transaction not found", code=404)
        
    return success_response(row, "Transaction updated successfully")


@router.delete("/{transaction_id}", response=Dict[str, Any])
def delete_transaction(request, transaction_id: int):
    """Delete a transaction permanently."""
    query = """
        DELETE FROM transactions
        WHERE transaction_id = %s
    """
    rows_affected = execute_modify(query, [transaction_id], log_name="delete_transaction")
    if rows_affected == 0:
        return error_response("Transaction not found", code=404)
    
    return success_response(None, "Transaction deleted successfully")


@router.get("/search/", response=Dict[str, Any])
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
    """Advanced transaction search."""
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

    sql_query += " ORDER BY t.date DESC LIMIT %s"
    params.append(limit)

    rows = run_select(sql_query, params, log_name="search_transactions")
    return {"status": "success", "count": len(rows), "data": rows}

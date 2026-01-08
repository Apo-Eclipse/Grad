"""Budgets database operations."""
import logging
from typing import Any, Dict, List, Optional

from ninja import Router, Query

from ..core.database import run_select, execute_modify, execute_modify_returning
from ..core.responses import success_response, error_response
from .schemas import BudgetCreateSchema, BudgetUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active budgets for a user (helper)."""
    query = """
        SELECT
            budget_id,
            budget_name,
            total_limit,
            priority_level_int
        FROM budget
        WHERE user_id = %s
          AND is_active = true
        ORDER BY priority_level_int DESC
    """
    return run_select(query, [user_id], log_name="fetch_active_budgets")


@router.get("/", response=List[Dict[str, Any]])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve active budgets for a user."""
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
        WHERE user_id = %s AND is_active = true
        ORDER BY priority_level_int DESC
    """
    return run_select(query, [user_id], log_name="get_budgets")


@router.post("/", response=Dict[str, Any])
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    query = """
        INSERT INTO budget (
            user_id,
            budget_name,
            description,
            total_limit,
            priority_level_int,
            is_active,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING
            budget_id,
            user_id,
            budget_name,
            total_limit,
            priority_level_int,
            is_active,
            created_at
    """
    params = [
        payload.user_id,
        payload.budget_name,
        payload.description,
        payload.total_limit,
        payload.priority_level_int,
        payload.is_active,
    ]
    
    success, _, row = execute_modify_returning(query, params, log_name="create_budget")
    if not success or row is None:
        return error_response("Failed to create budget")
    
    return success_response(row, "Budget created successfully")


@router.put("/{budget_id}", response=Dict[str, Any])
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # Add updated_at timestamp
    updates['updated_at'] = 'NOW()'
    
    # We need to handle NOW() properly since it's SQL not a param
    # simpler approach: remove updated_at from params and inject it in query string
    set_parts = []
    params = []
    
    for key, val in updates.items():
        if key == 'updated_at':
            set_parts.append("updated_at = NOW()")
        else:
            set_parts.append(f"{key} = %s")
            params.append(val)
    
    params.append(budget_id)
    set_clause = ", ".join(set_parts)

    query = f"""
        UPDATE budget
        SET {set_clause}
        WHERE budget_id = %s
        RETURNING *
    """

    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_budget")
    if not success:
        return error_response("Failed to update budget")
    if rows_affected == 0 or row is None:
        return error_response("Budget not found", code=404)
        
    return success_response(row, "Budget updated successfully")


@router.delete("/{budget_id}", response=Dict[str, Any])
def delete_budget(request, budget_id: int):
    """Soft delete a budget."""
    query = """
        UPDATE budget
        SET is_active = false, updated_at = NOW()
        WHERE budget_id = %s
    """
    rows_affected = execute_modify(query, [budget_id], log_name="delete_budget")
    if rows_affected == 0:
        return error_response("Budget not found", code=404)
    
    return success_response(None, "Budget deactivated successfully")

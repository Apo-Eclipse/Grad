"""Budget database endpoints."""
import logging
from typing import List, Dict, Any
from ninja import Router, Query
from personal_assistant_api.core.database import run_select, execute_modify_returning
from personal_assistant_api.database.schemas import BudgetSchema, BudgetCreateSchema
from personal_assistant_api.core.responses import success_response, error_response

logger = logging.getLogger(__name__)
router = Router()


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
    return run_select(query, [user_id])


@router.get("/", response=List[Dict[str, Any]])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve active user budgets only."""
    return fetch_active_budgets(user_id)


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
    success, _, row = execute_modify_returning(query, params, log_name="create_budget")
    if not success or row is None:
        return {"success": False, "error": "Failed to create budget"}
    return {"success": True, "budget": row}


@router.put("/{budget_id}", response=Dict[str, Any])
def update_budget(request, budget_id: int, payload: BudgetCreateSchema):
    """Update an existing budget."""
    query = """
        UPDATE budget SET
            budget_name = %s,
            description = %s,
            total_limit = %s,
            priority_level_int = %s,
            is_active = %s,
            updated_at = NOW()
        WHERE budget_id = %s
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
        payload.budget_name,
        payload.description,
        payload.total_limit,
        payload.priority_level_int,
        payload.is_active,
        budget_id,
    ]
    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_budget")
    if not success:
        return {"success": False, "error": "Failed to update budget"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Budget not found"}
    return {"success": True, "budget": row}


@router.delete("/{budget_id}", response=Dict[str, Any])
def delete_budget(request, budget_id: int):
    """Soft delete a budget by setting is_active to false."""
    query = """
        UPDATE budget
        SET is_active = false, updated_at = NOW()
        WHERE budget_id = %s
        RETURNING budget_id, budget_name, is_active, updated_at
    """
    success, rows_affected, row = execute_modify_returning(query, [budget_id], log_name="delete_budget")
    if not success:
        return {"success": False, "error": "Failed to update budget"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Budget not found"}
    return {"success": True, "message": "Budget marked as inactive", "budget": row}


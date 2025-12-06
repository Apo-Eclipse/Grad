"""Income database endpoints."""
import logging
from typing import List, Dict, Any
from ninja import Router, Query
from personal_assistant_api.core.database import run_select, execute_modify_returning
from personal_assistant_api.database.schemas import IncomeSchema, IncomeCreateSchema
from personal_assistant_api.core.responses import success_response, error_response

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
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
    return run_select(query, [user_id])


@router.get("/active", response=List[Dict[str, Any]])
def get_active_income(request, user_id: int = Query(...)):
    """Retrieve active income sources for a user."""
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
    return run_select(query, [user_id])


@router.post("/", response=Dict[str, Any])
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
    success, _, row = execute_modify_returning(query, params, log_name="create_income")
    if not success or row is None:
        return {"success": False, "error": "Failed to create income source"}
    return {"success": True, "message": "Income source created successfully", "income": row}


@router.put("/{income_id}", response=Dict[str, Any])
def update_income(request, income_id: int, payload: IncomeCreateSchema):
    """Update an existing income source."""
    query = """
        UPDATE income SET
            type_income = %s,
            amount = %s,
            description = %s,
            updated_at = NOW()
        WHERE income_id = %s
        RETURNING income_id, user_id, type_income, amount, description
    """
    params = [
        payload.type_income,
        payload.amount,
        payload.description,
        income_id,
    ]
    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_income")
    if not success:
        return {"success": False, "error": "Failed to update income source"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Income source not found"}
    return {"success": True, "income": row}


@router.delete("/{income_id}", response=Dict[str, Any])
def delete_income(request, income_id: int):
    """Delete an income source."""
    query = """
        DELETE FROM income
        WHERE income_id = %s
        RETURNING income_id
    """
    success, rows_affected, row = execute_modify_returning(query, [income_id], log_name="delete_income")
    if not success:
        return {"success": False, "error": "Failed to delete income source"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Income source not found"}
    return {"success": True, "message": "Income source deleted", "income_id": row["income_id"]}


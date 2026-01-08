"""Income database operations."""
import logging
from typing import Any, Dict, List

from ninja import Router, Query

from ..core.database import run_select, execute_modify_returning
from ..core.responses import success_response, error_response
from .schemas import IncomeCreateSchema

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
    return run_select(query, [user_id], log_name="get_income")


@router.get("/active", response=List[Dict[str, Any]])
def get_active_income(request, user_id: int = Query(...)):
    """Retrieve all income sources (alias for /)."""
    return get_income(request, user_id)


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
        return error_response("Failed to create income source")
    
    return success_response(row, "Income source created successfully")

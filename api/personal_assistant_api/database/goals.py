"""Goals database operations."""
import logging
from typing import Any, Dict, List, Optional

from ninja import Router, Query

from ..core.database import run_select, execute_modify, execute_modify_returning
from ..core.responses import success_response, error_response
from .schemas import GoalCreateSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
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
            plan,
            created_at,
            updated_at
        FROM goals
        WHERE user_id = %s
    """
    params: List[Any] = [user_id]
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    return run_select(query, params, log_name="get_goals")


@router.post("/", response=Dict[str, Any])
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
            status,
            plan,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING goal_id
    """
    params = [
        payload.user_id,
        payload.goal_name,
        payload.description,
        payload.target,
        payload.start_date,
        payload.due_date,
        payload.status,
        payload.plan,
    ]
    
    success, _, row = execute_modify_returning(query, params, log_name="create_goal")
    if not success or row is None:
        return error_response("Failed to create goal")
    
    return success_response(row, "Goal created successfully")


@router.delete("/{goal_id}", response=Dict[str, Any])
def delete_goal(request, goal_id: int):
    """Soft delete a goal."""
    query = """
        UPDATE goals
        SET status = 'inactive', updated_at = NOW()
        WHERE goal_id = %s
    """
    rows_affected = execute_modify(query, [goal_id], log_name="delete_goal")
    if rows_affected == 0:
        return error_response("Goal not found", code=404)
    
    return success_response(None, "Goal deactivated successfully")

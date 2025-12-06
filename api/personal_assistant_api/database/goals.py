"""Goal database endpoints."""
import logging
from typing import List, Optional, Dict, Any
from ninja import Router, Query
from personal_assistant_api.core.database import run_select, execute_modify_returning
from personal_assistant_api.database.schemas import GoalSchema, GoalCreateSchema
from personal_assistant_api.core.responses import success_response, error_response

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
    return run_select(query, params)


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
    success, _, row = execute_modify_returning(query, params, log_name="create_goal")
    if not success or row is None:
        return {"success": False, "error": "Failed to create goal"}
    return {"success": True, "goal": row}


@router.put("/{goal_id}", response=Dict[str, Any])
def update_goal(request, goal_id: int, payload: GoalCreateSchema):
    """Update an existing goal."""
    query = """
        UPDATE goals SET
            goal_name = %s,
            description = %s,
            target = %s,
            start_date = %s,
            due_date = %s,
            status = %s,
            updated_at = NOW()
        WHERE goal_id = %s
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
        payload.goal_name,
        payload.description,
        payload.target,
        payload.start_date,
        payload.due_date,
        payload.status,
        goal_id,
    ]
    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_goal")
    if not success:
        return {"success": False, "error": "Failed to update goal"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Goal not found"}
    return {"success": True, "goal": row}


@router.delete("/{goal_id}", response=Dict[str, Any])
def delete_goal(request, goal_id: int):
    """Soft delete a goal by setting status to 'inactive'."""
    query = """
        UPDATE goals
        SET status = 'inactive', updated_at = NOW()
        WHERE goal_id = %s
        RETURNING goal_id, goal_name, status, updated_at
    """
    success, rows_affected, row = execute_modify_returning(query, [goal_id], log_name="delete_goal")
    if not success:
        return {"success": False, "error": "Failed to update goal"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "Goal not found"}
    return {"success": True, "message": "Goal marked as inactive", "goal": row}


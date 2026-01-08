"""Users database operations."""
import logging
from typing import Any, Dict, List

from ninja import Router

from ..core.database import run_select, run_select_single, execute_modify_returning
from ..core.responses import success_response, error_response
from .schemas import UserCreateSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get("/{user_id}", response=Dict[str, Any])
def get_user(request, user_id: int):
    """Get user profile details."""
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
            created_at
        FROM users
        WHERE user_id = %s
    """
    row = run_select_single(query, [user_id], log_name="get_user")
    if not row:
        return error_response("User not found", code=404)
    return row


@router.get("/{user_id}/exists", response=Dict[str, Any])
def check_user_exists(request, user_id: int):
    """Check if a user ID exists."""
    query = "SELECT user_id, first_name, last_name FROM users WHERE user_id = %s"
    row = run_select_single(query, [user_id], log_name="check_user_exists")
    if row:
        return {"exists": True, "user": row}
    return {"exists": False}


@router.post("/", response=Dict[str, Any])
def create_user(request, payload: UserCreateSchema):
    """Create a new user."""
    if payload.user_id:
        # Manual ID
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
        # Auto-incremental ID
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

    success, _, row = execute_modify_returning(query, params, log_name="create_user")
    if not success or row is None:
        return error_response("Failed to create user")
    
    return success_response(row, "User created successfully")

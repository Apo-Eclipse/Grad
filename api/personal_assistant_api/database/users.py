"""User database endpoints."""
import logging
from typing import List, Dict, Any
from ninja import Router
from personal_assistant_api.core.database import run_select, run_select_single, execute_modify_returning
from personal_assistant_api.database.schemas import UserSchema, UserCreateSchema
from personal_assistant_api.core.responses import success_response, error_response

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
def get_users(request):
    """Retrieve all users."""
    sql = """
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
    """
    return run_select(sql)


@router.get("/{user_id}", response=Dict[str, Any])
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
    return run_select_single(query, [user_id], default={})


@router.get("/{user_id}/exists", response=Dict[str, Any])
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
    result = run_select_single(query, [user_id], default={})
    if result and result.get("user_id") is not None:
        return {
            "exists": True,
            "user_id": result.get("user_id"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
        }
    return {"exists": False, "user_id": user_id}


@router.post("/", response=Dict[str, Any])
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
    success, _, row = execute_modify_returning(query, params, log_name="create_user")
    if not success or row is None:
        return {"success": False, "error": "Failed to create user"}
    return {"success": True, "message": "User created successfully", "user": row}


@router.put("/{user_id}", response=Dict[str, Any])
def update_user(request, user_id: int, payload: UserCreateSchema):
    """Update an existing user."""
    query = """
        UPDATE users SET
            first_name = %s,
            last_name = %s,
            job_title = %s,
            address = %s,
            birthday = %s,
            gender = %s,
            employment_status = %s,
            education_level = %s,
            updated_at = NOW()
        WHERE user_id = %s
        RETURNING user_id, first_name, last_name, job_title, employment_status
    """
    params = [
        payload.first_name,
        payload.last_name,
        payload.job_title,
        payload.address,
        payload.birthday,
        payload.gender,
        payload.employment_status,
        payload.education_level,
        user_id,
    ]
    success, rows_affected, row = execute_modify_returning(query, params, log_name="update_user")
    if not success:
        return {"success": False, "error": "Failed to update user"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "User not found"}
    return {"success": True, "user": row}


@router.delete("/{user_id}", response=Dict[str, Any])
def delete_user(request, user_id: int):
    """Delete a user."""
    query = """
        DELETE FROM users
        WHERE user_id = %s
        RETURNING user_id
    """
    success, rows_affected, row = execute_modify_returning(query, [user_id], log_name="delete_user")
    if not success:
        return {"success": False, "error": "Failed to delete user"}
    if rows_affected == 0 or row is None:
        return {"success": False, "error": "User not found"}
    return {"success": True, "message": "User deleted", "user_id": row["user_id"]}


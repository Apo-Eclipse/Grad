from ninja import Router
from typing import List
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.database.schemas import UserSchema
from personal_assistant_api.core.responses import success_response, error_response

router = Router()

@router.get("/", response=List[UserSchema])
def get_users(request):
    sql = "SELECT * FROM users"
    return run_select(sql)

@router.get("/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    sql = "SELECT * FROM users WHERE user_id = %s"
    results = run_select(sql, [user_id])
    if not results:
        return error_response("User not found", 404)
    return results[0]

@router.post("/")
def create_user(request, payload: UserSchema):
    sql = """
        INSERT INTO users (first_name, last_name, job_title, address, description)
        VALUES (%s, %s, %s, %s, %s)
    """
    params = [
        payload.first_name, payload.last_name, payload.job_title, 
        payload.address, payload.description
    ]
    count = execute_modify(sql, params)
    return success_response({"inserted": count})

@router.put("/{user_id}")
def update_user(request, user_id: int, payload: UserSchema):
    sql = """
        UPDATE users SET 
        first_name=%s, last_name=%s, job_title=%s, address=%s, description=%s
        WHERE user_id = %s
    """
    params = [
        payload.first_name, payload.last_name, payload.job_title, 
        payload.address, payload.description, user_id
    ]
    count = execute_modify(sql, params)
    return success_response({"updated": count})

@router.delete("/{user_id}")
def delete_user(request, user_id: int):
    sql = "DELETE FROM users WHERE user_id = %s"
    count = execute_modify(sql, [user_id])
    return success_response({"deleted": count})

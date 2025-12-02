from ninja import Router
from typing import List
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.database.schemas import GoalSchema
from personal_assistant_api.core.responses import success_response, error_response

router = Router()

@router.get("/", response=List[GoalSchema])
def get_goals(request, user_id: int):
    sql = "SELECT * FROM goals WHERE user_id = %s"
    return run_select(sql, [user_id])

@router.post("/")
def create_goal(request, payload: GoalSchema):
    sql = """
        INSERT INTO goals (user_id, goal_name, description, target, current, start_date, due_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = [
        payload.user_id, payload.goal_name, payload.description, 
        payload.target, payload.current, payload.start_date, 
        payload.due_date, payload.status
    ]
    count = execute_modify(sql, params)
    return success_response({"inserted": count})

@router.put("/{goal_id}")
def update_goal(request, goal_id: int, payload: GoalSchema):
    sql = """
        UPDATE goals SET 
        goal_name=%s, description=%s, target=%s, current=%s, 
        start_date=%s, due_date=%s, status=%s
        WHERE goal_id = %s
    """
    params = [
        payload.goal_name, payload.description, payload.target, 
        payload.current, payload.start_date, payload.due_date, 
        payload.status, goal_id
    ]
    count = execute_modify(sql, params)
    return success_response({"updated": count})

@router.delete("/{goal_id}")
def delete_goal(request, goal_id: int):
    sql = "DELETE FROM goals WHERE goal_id = %s"
    count = execute_modify(sql, [goal_id])
    return success_response({"deleted": count})

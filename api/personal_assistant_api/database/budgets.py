from ninja import Router
from typing import List
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.database.schemas import BudgetSchema
from personal_assistant_api.core.responses import success_response, error_response

router = Router()

@router.get("/", response=List[BudgetSchema])
def get_budgets(request, user_id: int):
    sql = "SELECT * FROM budget WHERE user_id = %s"
    return run_select(sql, [user_id])

@router.post("/")
def create_budget(request, payload: BudgetSchema):
    sql = """
        INSERT INTO budget (user_id, budget_name, description, total_limit, priority_level_int, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = [
        payload.user_id, payload.budget_name, payload.description, 
        payload.total_limit, payload.priority_level_int, payload.is_active
    ]
    count = execute_modify(sql, params)
    return success_response({"inserted": count})

@router.put("/{budget_id}")
def update_budget(request, budget_id: int, payload: BudgetSchema):
    sql = """
        UPDATE budget SET 
        budget_name=%s, description=%s, total_limit=%s, 
        priority_level_int=%s, is_active=%s
        WHERE budget_id = %s
    """
    params = [
        payload.budget_name, payload.description, payload.total_limit, 
        payload.priority_level_int, payload.is_active, budget_id
    ]
    count = execute_modify(sql, params)
    return success_response({"updated": count})

@router.delete("/{budget_id}")
def delete_budget(request, budget_id: int):
    sql = "DELETE FROM budget WHERE budget_id = %s"
    count = execute_modify(sql, [budget_id])
    return success_response({"deleted": count})

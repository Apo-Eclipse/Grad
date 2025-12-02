from ninja import Router
from typing import List
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.database.schemas import IncomeSchema
from personal_assistant_api.core.responses import success_response, error_response

router = Router()

@router.get("/", response=List[IncomeSchema])
def get_income(request, user_id: int):
    sql = "SELECT * FROM income WHERE user_id = %s"
    return run_select(sql, [user_id])

@router.post("/")
def create_income(request, payload: IncomeSchema):
    sql = """
        INSERT INTO income (user_id, type_income, amount, description)
        VALUES (%s, %s, %s, %s)
    """
    params = [
        payload.user_id, payload.type_income, payload.amount, payload.description
    ]
    count = execute_modify(sql, params)
    return success_response({"inserted": count})

@router.put("/{income_id}")
def update_income(request, income_id: int, payload: IncomeSchema):
    sql = """
        UPDATE income SET 
        type_income=%s, amount=%s, description=%s
        WHERE income_id = %s
    """
    params = [
        payload.type_income, payload.amount, payload.description, income_id
    ]
    count = execute_modify(sql, params)
    return success_response({"updated": count})

@router.delete("/{income_id}")
def delete_income(request, income_id: int):
    sql = "DELETE FROM income WHERE income_id = %s"
    count = execute_modify(sql, [income_id])
    return success_response({"deleted": count})

from ninja import Router, Schema
from typing import Any, Dict, List
from personal_assistant_api.core.database import run_select

router = Router()

class SQLQuerySchema(Schema):
    query: str

@router.post("/execute_sql")
def execute_custom_sql(request, payload: SQLQuerySchema):
    # WARNING: This is dangerous and should be restricted to read-only in production
    # or validated strictly. For now, assuming internal use.
    return run_select(payload.query)

@router.get("/spending_by_category")
def spending_by_category(request, user_id: int):
    sql = """
        SELECT type_spending, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = %s 
        GROUP BY type_spending
    """
    return run_select(sql, [user_id])

@router.get("/monthly_spending")
def monthly_spending(request, user_id: int):
    sql = """
        SELECT DATE_TRUNC('month', date) as month, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = %s 
        GROUP BY month 
        ORDER BY month DESC
    """
    return run_select(sql, [user_id])

from ninja import Router
from typing import List, Optional
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.database.schemas import TransactionSchema, TransactionCreateSchema
from personal_assistant_api.core.responses import success_response, error_response

router = Router()

@router.get("/", response=List[TransactionSchema])
def get_transactions(request, user_id: int, limit: int = 100, offset: int = 0):
    sql = "SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT %s OFFSET %s"
    return run_select(sql, [user_id, limit, offset])

@router.post("/")
def create_transaction(request, payload: TransactionCreateSchema):
    sql = """
        INSERT INTO transactions (date, amount, time, store_name, city, neighbourhood, type_spending, user_id, budget_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = [
        payload.date, payload.amount, payload.time, payload.store_name, 
        payload.city, payload.neighbourhood, payload.type_spending, 
        payload.user_id, payload.budget_id
    ]
    count = execute_modify(sql, params)
    return success_response({"inserted": count})

@router.get("/{transaction_id}", response=TransactionSchema)
def get_transaction(request, transaction_id: int):
    sql = "SELECT * FROM transactions WHERE transaction_id = %s"
    results = run_select(sql, [transaction_id])
    if not results:
        return error_response("Transaction not found", 404)
    return results[0]

@router.put("/{transaction_id}")
def update_transaction(request, transaction_id: int, payload: TransactionCreateSchema):
    sql = """
        UPDATE transactions SET 
        date=%s, amount=%s, time=%s, store_name=%s, city=%s, 
        neighbourhood=%s, type_spending=%s, user_id=%s, budget_id=%s
        WHERE transaction_id = %s
    """
    params = [
        payload.date, payload.amount, payload.time, payload.store_name, 
        payload.city, payload.neighbourhood, payload.type_spending, 
        payload.user_id, payload.budget_id, transaction_id
    ]
    count = execute_modify(sql, params)
    return success_response({"updated": count})

@router.delete("/{transaction_id}")
def delete_transaction(request, transaction_id: int):
    sql = "DELETE FROM transactions WHERE transaction_id = %s"
    count = execute_modify(sql, [transaction_id])
    return success_response({"deleted": count})

@router.get("/search/")
def search_transactions(request, query: str):
    sql = "SELECT * FROM transactions WHERE store_name ILIKE %s OR city ILIKE %s"
    pattern = f"%{query}%"
    return run_select(sql, [pattern, pattern])

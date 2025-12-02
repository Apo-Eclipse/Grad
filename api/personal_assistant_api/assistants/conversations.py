from ninja import Router, Schema
from typing import List
from personal_assistant_api.core.database import run_select, execute_modify
from personal_assistant_api.core.responses import success_response

router = Router()

class ConversationCreateSchema(Schema):
    user_id: int
    title: str = "New Conversation"

@router.post("/start")
def start_conversation(request, payload: ConversationCreateSchema):
    sql = "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING conversation_id"
    # Note: execute_modify returns rowcount, not ID. 
    # For RETURNING, we should use run_select
    result = run_select(sql, [payload.user_id, payload.title])
    if result:
        return success_response({"conversation_id": result[0]['conversation_id']})
    return success_response({"status": "created"})

@router.post("/{conversation_id}/message")
def add_message(request, conversation_id: int, role: str, content: str):
    sql = "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)"
    execute_modify(sql, [conversation_id, role, content])
    return success_response({"status": "added"})

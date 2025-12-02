from ninja import Router
from personal_assistant_api.core.database import run_select

router = Router()

@router.get("/")
def get_conversations(request, user_id: int):
    sql = "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC"
    return run_select(sql, [user_id])

@router.get("/{conversation_id}/messages")
def get_messages(request, conversation_id: int):
    sql = "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC"
    return run_select(sql, [conversation_id])

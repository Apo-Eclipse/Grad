"""Manual conversation management endpoints."""
import logging
from typing import Any, Dict

from ninja import Router

from .schemas import ConversationStartSchema, ConversationResponseSchema
from ..core.database import execute_modify_returning, execute_modify

logger = logging.getLogger(__name__)
router = Router()


@router.post("/start", response=ConversationResponseSchema)
def start_conversation_endpoint(request, payload: ConversationStartSchema):
    """Start a new conversation (alias to assistants/api specific one if needed separately)."""
    query = """
        INSERT INTO chat_conversations (user_id, channel, started_at, last_message_at)
        VALUES (%s, %s, NOW(), NOW())
        RETURNING conversation_id, user_id, channel, started_at
    """
    success, _, row = execute_modify_returning(
        query, 
        [payload.user_id, payload.channel], 
        log_name="start_conversation_manual"
    )
    if not success or not row:
        raise Exception("Failed to start conversation")
    return row


@router.post("/{conversation_id}/message", response=Dict[str, Any])
def add_message(request, conversation_id: int, role: str, content: str):
    """Manually add a message to history (useful for testing or external inputs)."""
    query = """
        INSERT INTO chat_messages (conversation_id, sender_type, content, created_at)
        VALUES (%s, %s, %s, NOW())
    """
    rows = execute_modify(query, [conversation_id, role, content], log_name="add_message")
    if rows:
        return {"success": True, "message": "Message added"}
    return {"success": False, "error": "Failed to add message"}

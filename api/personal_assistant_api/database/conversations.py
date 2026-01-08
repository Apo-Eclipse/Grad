"""Conversations database operations."""
import logging
from typing import Any, Dict, List

from ninja import Router, Query

from ..core.database import run_select

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
def get_conversations(request, user_id: int = Query(...), limit: int = Query(50)):
    """Retrieve chat conversations for a user."""
    query = """
        SELECT
            conversation_id,
            title,
            channel,
            started_at,
            last_message_at
        FROM chat_conversations
        WHERE user_id = %s
        ORDER BY last_message_at DESC NULLS LAST
        LIMIT %s
    """
    return run_select(query, [user_id, limit], log_name="get_conversations")


@router.get("/{conversation_id}/messages", response=List[Dict[str, Any]])
def get_messages(request, conversation_id: int, limit: int = Query(100)):
    """Retrieve messages for a conversation."""
    query = """
        SELECT
            message_id,
            conversation_id,
            sender_type,
            source_agent,
            content,
            content_type,
            created_at
        FROM chat_messages
        WHERE conversation_id = %s
        ORDER BY message_id ASC
        LIMIT %s
    """
    return run_select(query, [conversation_id, limit], log_name="get_messages")

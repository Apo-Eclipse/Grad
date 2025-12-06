"""Conversation database endpoints."""
import logging
from typing import List, Dict, Any
from ninja import Router, Query
from personal_assistant_api.core.database import run_select

logger = logging.getLogger(__name__)
router = Router()


@router.get("/", response=List[Dict[str, Any]])
def get_conversations(request, user_id: int = Query(...), limit: int = Query(50, le=500)):
    """Retrieve chat conversations for a user."""
    query = """
        SELECT
            conversation_id,
            user_id,
            title,
            channel,
            started_at,
            last_message_at,
            summary_text,
            summary_created_at
        FROM chat_conversations
        WHERE user_id = %s
        ORDER BY last_message_at DESC
        LIMIT %s
    """
    return run_select(query, [user_id, limit])


@router.get("/{conversation_id}/messages", response=List[Dict[str, Any]])
def get_messages(request, conversation_id: int, limit: int = Query(100, le=1000)):
    """Retrieve messages from a conversation."""
    query = """
        SELECT
            message_id,
            conversation_id,
            sender_type,
            source_agent,
            content,
            content_type,
            language,
            created_at
        FROM chat_messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return run_select(query, [conversation_id, limit])


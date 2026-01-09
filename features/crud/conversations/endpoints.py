"""Conversation management endpoints (CRUD + Manual)."""

import logging
from typing import Any, Dict

from ninja import Router, Query

from core.models import ChatConversation, ChatMessage
from core.utils.responses import success_response, error_response
from .service import insert_chat_message

logger = logging.getLogger(__name__)
router = Router()

# --- CRUD Endpoints ---


@router.get("/", response=Dict[str, Any])
def get_conversations(request, user_id: int = Query(...), limit: int = Query(50)):
    """Retrieve chat conversations for a user."""
    conversations = (
        ChatConversation.objects.filter(user_id=user_id)
        .order_by("-last_message_at")
        .values("id", "title", "channel", "started_at", "last_message_at")[:limit]
    )
    return success_response(list(conversations))


@router.get("/{conversation_id}", response=Dict[str, Any])
def get_conversation(request, conversation_id: int):
    """Get a single conversation."""
    conv = (
        ChatConversation.objects.filter(id=conversation_id)
        .values("id", "user_id", "title", "channel", "started_at", "last_message_at")
        .first()
    )
    if not conv:
        return error_response("Conversation not found", code=404)
    return success_response(conv)


@router.get("/{conversation_id}/messages", response=Dict[str, Any])
def get_messages(request, conversation_id: int, limit: int = Query(100)):
    """Retrieve messages for a conversation."""
    messages = (
        ChatMessage.objects.filter(conversation_id=conversation_id)
        .order_by("id")
        .values(
            "id",
            "conversation_id",
            "sender_type",
            "source_agent",
            "content",
            "content_type",
            "created_at",
        )[:limit]
    )
    return success_response(list(messages))


# --- Manual/Testing Endpoints ---


@router.post("/{conversation_id}/message", response=Dict[str, Any])
def add_message(request, conversation_id: int, role: str, content: str):
    """Manually add a message to history (useful for testing or external inputs)."""
    try:
        insert_chat_message(
            conversation_id=conversation_id,
            sender_type=role,
            source_agent="Manual",
            content=content,
        )
        return {"success": True, "message": "Message added"}
    except Exception as e:
        logger.exception("Failed to add message")
        return {"success": False, "error": str(e)}

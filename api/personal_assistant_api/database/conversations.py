"""Conversations database operations."""

import logging
from typing import Any, Dict

from ninja import Router, Query

from ..models import ChatConversation, ChatMessage
from ..core.responses import success_response, error_response

logger = logging.getLogger(__name__)
router = Router()


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
    try:
        conv = ChatConversation.objects.get(id=conversation_id)
        return success_response(
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "title": conv.title,
                "channel": conv.channel,
                "started_at": conv.started_at,
                "last_message_at": conv.last_message_at,
            }
        )
    except ChatConversation.DoesNotExist:
        return error_response("Conversation not found", code=404)


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

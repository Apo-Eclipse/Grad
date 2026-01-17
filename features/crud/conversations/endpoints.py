"""Conversation management endpoints (CRUD + Manual)."""

import logging
from typing import Any, Dict

from ninja import Router, Query

from core.models import ChatConversation, ChatMessage
from core.utils.responses import success_response, error_response
from django.utils import timezone
from .schemas import ConversationStartSchema, ConversationResponseSchema
from .service import insert_chat_message

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# --- Manual/Testing Endpoints ---

@router.api_operation(["POST", "GET"], "/start", response=ConversationResponseSchema)
def start_conversation(request, payload: ConversationStartSchema = None):
    """Start a new conversation thread."""
    try:
        channel = payload.channel if payload else "web"
        conversation = ChatConversation.objects.create(
            user_id=request.user.id,
            channel=channel,
            last_message_at=timezone.now(),
        )
        return {
            "conversation_id": conversation.id,
            "user_id": conversation.user_id,
            "channel": conversation.channel,
            "started_at": conversation.started_at,
        }
    except Exception as e:
        logger.exception("Failed to start conversation")
        raise Exception(f"Failed to start conversation: {e}")


# --- CRUD Endpoints ---


@router.get("/", response=Dict[str, Any])
def get_conversations(request, limit: int = Query(50)):
    """Retrieve chat conversations for a user."""
    conversations = (
        ChatConversation.objects.filter(user_id=request.user.id)
        .order_by("-last_message_at")
        .values("id", "title", "channel", "started_at", "last_message_at")[:limit]
    )
    return success_response(list(conversations))


@router.get("/{conversation_id}", response=Dict[str, Any])
def get_conversation(request, conversation_id: int):
    """Get a single conversation."""
    conv = (
        ChatConversation.objects.filter(id=conversation_id, user_id=request.user.id)
        .values("id", "user_id", "title", "channel", "started_at", "last_message_at")
        .first()
    )
    if not conv:
        return error_response("Conversation not found", code=404)
    return success_response(conv)


@router.get("/{conversation_id}/messages", response=Dict[str, Any])
def get_messages(request, conversation_id: int, limit: int = Query(100)):
    """Retrieve messages for a conversation."""
    # Ensure conversation belongs to user
    if not ChatConversation.objects.filter(
        id=conversation_id, user_id=request.user.id
    ).exists():
        return error_response("Conversation not found", code=404)

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
    # Ensure conversation belongs to user
    if not ChatConversation.objects.filter(
        id=conversation_id, user_id=request.user.id
    ).exists():
        return {"success": False, "error": "Conversation not found"}

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

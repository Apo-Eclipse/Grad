"""Conversation management endpoints (CRUD + Manual)."""

import logging
from typing import Any, Dict
from asgiref.sync import sync_to_async

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
async def start_conversation(request, payload: ConversationStartSchema = None):
    """Start a new conversation thread."""
    channel = payload.channel if payload else "web"

    try:
        conversation = await ChatConversation.objects.acreate(
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
async def get_conversations(request, limit: int = Query(50)):
    """Retrieve chat conversations for a user."""
    conversations = []
    count = 0
    async for conv in (
        ChatConversation.objects.filter(user_id=request.user.id)
        .order_by("-last_message_at")
        .values("id", "title", "channel", "started_at", "last_message_at")
    ):
        if count >= limit:
            break
        conversations.append(conv)
        count += 1

    return success_response(conversations)


@router.get("/{conversation_id}", response=Dict[str, Any])
async def get_conversation(request, conversation_id: int):
    """Get a single conversation."""
    conv = await (
        ChatConversation.objects.filter(id=conversation_id, user_id=request.user.id)
        .values("id", "user_id", "title", "channel", "started_at", "last_message_at")
        .afirst()
    )
    if not conv:
        return error_response("Conversation not found", code=404)
    return success_response(conv)


@router.get("/{conversation_id}/messages", response=Dict[str, Any])
async def get_messages(request, conversation_id: int, limit: int = Query(100)):
    """Retrieve messages for a conversation."""
    # Ensure conversation belongs to user
    conv_exists = await ChatConversation.objects.filter(
        id=conversation_id, user_id=request.user.id
    ).aexists()
    if not conv_exists:
        return error_response("Conversation not found", code=404)

    messages = []
    count = 0
    async for msg in (
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
        )
    ):
        if count >= limit:
            break
        messages.append(msg)
        count += 1

    return success_response(messages)


# --- Manual/Testing Endpoints ---


@router.post("/{conversation_id}/message", response=Dict[str, Any])
async def add_message(request, conversation_id: int, role: str, content: str):
    """Manually add a message to history (useful for testing or external inputs)."""
    # Ensure conversation belongs to user
    conv_exists = await ChatConversation.objects.filter(
        id=conversation_id, user_id=request.user.id
    ).aexists()
    if not conv_exists:
        return {"success": False, "error": "Conversation not found"}

    # insert_chat_message is sync, wrap it
    @sync_to_async
    def add_message_sync():
        try:
            insert_chat_message(
                conversation_id=conversation_id,
                sender_type=role,
                source_agent="Manual",
                content=content,
            )
            return True, None
        except Exception as e:
            logger.exception("Failed to add message")
            return False, str(e)

    success, error = await add_message_sync()
    if not success:
        return {"success": False, "error": error}
    return {"success": True, "message": "Message added"}

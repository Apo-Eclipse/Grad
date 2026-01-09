"""Manual conversation management endpoints."""

import logging
from typing import Any, Dict

from ninja import Router

from ..models import ChatMessage

logger = logging.getLogger(__name__)
router = Router()


# NOTE: start_conversation is in assistants/api.py (main API)


@router.post("/{conversation_id}/message", response=Dict[str, Any])
def add_message(request, conversation_id: int, role: str, content: str):
    """Manually add a message to history (useful for testing or external inputs)."""
    try:
        ChatMessage.objects.create(
            conversation_id=conversation_id,
            sender_type=role,
            source_agent="Manual",
            content=content,
        )
        return {"success": True, "message": "Message added"}
    except Exception as e:
        logger.exception("Failed to add message")
        return {"success": False, "error": str(e)}

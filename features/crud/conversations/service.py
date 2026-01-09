import logging
from typing import List
from datetime import datetime

from core.models import ChatMessage

logger = logging.getLogger(__name__)


def insert_chat_message(
    conversation_id: int,
    sender_type: str,
    source_agent: str,
    content: str,
    content_type: str = "text",
    language: str = "en",
    created_at: datetime = None,
) -> ChatMessage:
    """Insert a single chat message row using Django ORM."""
    return ChatMessage.objects.create(
        conversation_id=conversation_id,
        sender_type=sender_type,
        source_agent=source_agent,
        content=content,
        content_type=content_type,
        language=language,
    )


def get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
    """
    Retrieve the last N messages formatted as 'Sender: Content'.
    Useful for LLM memory context.
    """
    try:
        # Use .values() for faster loading
        messages = (
            ChatMessage.objects.filter(conversation_id=conversation_id)
            .order_by("id")
            .values("content_type", "source_agent", "sender_type", "content")[:limit]
        )

        if not messages:
            return "No previous messages in this conversation."

        lines: List[str] = []
        for idx, msg in enumerate(messages, start=1):
            if msg["content_type"] == "json":
                continue

            # Label by source_agent if possible, else sender_type
            sender_label = msg["source_agent"] or msg["sender_type"] or "Unknown"
            lines.append(f"{idx}. [{sender_label}] {msg['content']}")

        return (
            "\n".join(lines)
            if lines
            else "No previous text messages in this conversation."
        )

    except Exception as exc:
        logger.warning(
            "Failed to load conversation summary for %s: %s", conversation_id, exc
        )
        return "No previous messages (error while loading history)."

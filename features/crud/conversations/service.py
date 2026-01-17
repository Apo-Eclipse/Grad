import logging
from datetime import datetime
from typing import Optional

from core.models import ChatMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Data Operations
# =============================================================================


def insert_chat_message(
    conversation_id: int,
    sender_type: str,
    source_agent: str,
    content: str,
    content_type: str = "text",
    language: str = "en",
    created_at: Optional[datetime] = None,
) -> ChatMessage:
    """
    Insert a single chat message row using Django ORM.

    Args:
        conversation_id: The conversation this message belongs to.
        sender_type: Type of sender (e.g., 'user', 'assistant').
        source_agent: The agent that generated this message.
        content: The message content.
        content_type: Type of content (default 'text').
        language: Language code (default 'en').
        created_at: Optional custom timestamp (uses auto_now_add if None).

    Returns:
        The created ChatMessage instance.
    """
    message_data = {
        "conversation_id": conversation_id,
        "sender_type": sender_type,
        "source_agent": source_agent,
        "content": content,
        "content_type": content_type,
        "language": language,
    }

    # Only include created_at if explicitly provided
    if created_at is not None:
        message_data["created_at"] = created_at

    return ChatMessage.objects.create(**message_data)


def fetch_recent_messages(
    conversation_id: int,
    limit: int = 20,
    exclude_content_types: Optional[list[str]] = None,
) -> list[dict]:
    """
    Fetch the last N messages for a conversation.

    Args:
        conversation_id: The conversation ID.
        limit: Maximum number of messages to fetch.
        exclude_content_types: Content types to exclude (e.g., ['json']).

    Returns:
        List of message dicts in chronological order (oldest first).
    """
    queryset = ChatMessage.objects.filter(conversation_id=conversation_id)

    # Apply content type exclusions
    if exclude_content_types:
        queryset = queryset.exclude(content_type__in=exclude_content_types)

    # Get last N messages by ordering descending, then reverse for chronological order
    messages = list(
        queryset.order_by("-id").values(
            "content_type", "source_agent", "sender_type", "content"
        )[:limit]
    )

    # Reverse to get chronological order (oldest first)
    return list(reversed(messages))


# =============================================================================
# Formatting Functions
# =============================================================================


def format_message(index: int, message: dict) -> str:
    """
    Format a single message for display.

    Args:
        index: The message number (1-indexed).
        message: Message dict with source_agent, sender_type, content.

    Returns:
        Formatted string like "1. [AgentName] Message content"
    """
    sender_label = (
        message.get("source_agent") or message.get("sender_type") or "Unknown"
    )
    return f"{index}. [{sender_label}] {message['content']}"


def format_messages_list(messages: list[dict]) -> str:
    """
    Format a list of messages into a numbered conversation string.

    Args:
        messages: List of message dicts.

    Returns:
        Formatted conversation string with numbered messages.
    """
    if not messages:
        return "No previous text messages in this conversation."

    lines = [format_message(idx, msg) for idx, msg in enumerate(messages, start=1)]

    return "\n".join(lines)


# =============================================================================
# Main Orchestrator
# =============================================================================


def get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
    """
    Retrieve the last N messages formatted as 'Sender: Content'.
    Useful for LLM memory context.

    Args:
        conversation_id: The conversation ID.
        limit: Maximum number of messages to include.

    Returns:
        Formatted conversation summary string.
    """
    try:
        messages = fetch_recent_messages(
            conversation_id=conversation_id,
            limit=limit,
            exclude_content_types=["json"],
        )

        if not messages:
            return "No previous messages in this conversation."

        return format_messages_list(messages)

    except Exception as exc:
        logger.warning(
            "Failed to load conversation summary for %s: %s", conversation_id, exc
        )
        return "No previous messages (error while loading history)."


def fetch_latest_state(conversation_id: int) -> Optional[str]:
    """
    Fetch the most recent JSON state message for a conversation.

    This is useful for agents that incrementally build structured data
    (e.g., goal creation where fields are filled one at a time).

    Args:
        conversation_id: The conversation ID.

    Returns:
        The latest JSON content string, or None if no JSON state exists.
    """
    return (
        ChatMessage.objects.filter(
            conversation_id=conversation_id,
            content_type="json",
        )
        .order_by("-id")
        .values_list("content", flat=True)
        .first()
    )


def get_conversation_context(conversation_id: int, limit: int = 20) -> dict:
    """
    Get both conversation history AND current state for an LLM agent.

    This provides everything an agent needs to continue a goal-building
    or form-filling conversation:
    - history: The text conversation (what was said)
    - current_state: The latest JSON state (what's been filled so far)

    Args:
        conversation_id: The conversation ID.
        limit: Maximum number of text messages to include in history.

    Returns:
        dict with:
            - 'history': Formatted text conversation string
            - 'current_state': Latest JSON state string (or None)
    """
    try:
        history = get_conversation_summary(conversation_id, limit)
        current_state = fetch_latest_state(conversation_id)

        return {
            "history": history,
            "current_state": current_state,
        }

    except Exception as exc:
        logger.warning(
            "Failed to load conversation context for %s: %s", conversation_id, exc
        )
        return {
            "history": "No previous messages (error while loading history).",
            "current_state": None,
        }

"""Budget Maker API endpoints."""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from ninja import Router
from django.db import connection

from personal_assistant_api.assistants.maker_schemas import (
    BudgetMakerRequestSchema,
    BudgetMakerResponseSchema,
)
from personal_assistant_api.assistants.schemas import AnalysisErrorSchema
from personal_assistant_api.assistants.helpers import (
    get_user_summary,
    get_conversation_summary,
)
from agents.budget_maker import Budget_maker_agent

logger = logging.getLogger(__name__)
router = Router()


def _insert_chat_message(
    cursor,
    *,
    conversation_id: int,
    sender_type: str,
    source_agent: str,
    content: str,
    content_type: str = "text",
    language: str = "en",
    created_at: datetime,
) -> None:
    """Insert a single chat message row."""
    cursor.execute(
        """
            INSERT INTO chat_messages (
                conversation_id,
                sender_type,
                source_agent,
                content,
                content_type,
                language,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        [
            conversation_id,
            sender_type,
            source_agent,
            content,
            content_type,
            language,
            created_at,
        ],
    )


@router.post("/assist", response={200: BudgetMakerResponseSchema, 400: AnalysisErrorSchema, 500: AnalysisErrorSchema})
def budget_assist(request, payload: BudgetMakerRequestSchema):
    """
    Handle a budget-making conversation with memory using the Budget Maker agent.
    """
    try:
        if not payload.user_request or not payload.user_request.strip():
            return 400, {
                "error": "INVALID_REQUEST",
                "message": "user_request cannot be empty",
                "timestamp": datetime.now(),
            }

        conversation_id = payload.conversation_id

        if conversation_id is None:
            return 400, {
                "error": "CONVERSATION_REQUIRED",
                "message": "conversation_id is required. Call /personal_assistant/conversations/start first.",
                "timestamp": datetime.now(),
            }

        # Build memory context for the agent
        user_info = get_user_summary(payload.user_id)
        last_conversation = get_conversation_summary(conversation_id)

        agent_input = {
            "user_info": user_info,
            "last_conversation": last_conversation,
            "current_date": datetime.now().date().isoformat(),
            "user_request": payload.user_request,
        }

        budget_result = Budget_maker_agent.invoke(agent_input)

        # Persist this turn
        with connection.cursor() as cursor:
            now = datetime.now()
            # User message
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="user",
                source_agent="User",
                content=payload.user_request,
                created_at=now,
            )

            # BudgetMaker reply
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent="BudgetMaker",
                content=budget_result.message,
                created_at=now,
            )

            # Optional structured budget payload
            budget_payload: Dict[str, Any] = {
                "budget_name": budget_result.budget_name,
                "total_limit": budget_result.total_limit,
                "description": budget_result.description,
                "priority_level_int": budget_result.priority_level_int,
            }
            if any(budget_payload.values()):
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="BudgetMaker",
                    content=json.dumps(budget_payload),
                    content_type="json",
                    created_at=now,
                )

            cursor.execute(
                """
                UPDATE chat_conversations
                SET last_message_at = %s
                WHERE conversation_id = %s
            """,
                [now, conversation_id],
            )
            connection.commit()

        response: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "message": budget_result.message,
            "budget_name": budget_result.budget_name,
            "total_limit": budget_result.total_limit,
            "description": budget_result.description,
            "priority_level_int": budget_result.priority_level_int,
            "is_done": getattr(budget_result, "is_done", False),
        }
        return 200, response

    except Exception as exc:
        logger.error("Error in budget_assist: %s", exc, exc_info=True)
        return 500, {
            "error": "BUDGET_MAKER_ERROR",
            "message": str(exc),
            "timestamp": datetime.now(),
        }


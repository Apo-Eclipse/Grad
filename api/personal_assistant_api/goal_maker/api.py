"""Goal Maker API endpoints."""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from ninja import Router
from django.db import connection

from personal_assistant_api.assistants.maker_schemas import (
    GoalMakerRequestSchema,
    GoalMakerResponseSchema,
)
from personal_assistant_api.assistants.schemas import AnalysisErrorSchema
from personal_assistant_api.assistants.helpers import (
    get_user_summary,
    get_conversation_summary,
)
from agents.goal_maker import Goal_maker_agent

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


@router.post("/assist", response={200: GoalMakerResponseSchema, 400: AnalysisErrorSchema, 500: AnalysisErrorSchema})
def goals_assist(request, payload: GoalMakerRequestSchema):
    """
    Handle a goal-making conversation with memory using the Goal Maker agent.

    - Requires an existing conversation_id.
    - Stores user and assistant messages in chat_messages.
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

        goal_result = Goal_maker_agent.invoke(agent_input)

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

            # GoalMaker reply
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent="GoalMaker",
                content=goal_result.message,
                created_at=now,
            )

            # Optional structured goal payload
            goal_payload: Dict[str, Any] = {
                "goal_name": goal_result.goal_name,
                "target": goal_result.target,
                "goal_description": goal_result.goal_description,
                "due_date": goal_result.due_date,
            }
            if any(goal_payload.values()):
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="GoalMaker",
                    content=json.dumps(goal_payload),
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
            "message": goal_result.message,
            "goal_name": goal_result.goal_name,
            "target": goal_result.target,
            "goal_description": goal_result.goal_description,
            "due_date": goal_result.due_date,
            "is_done": getattr(goal_result, "is_done", False),
        }
        return 200, response

    except Exception as exc:
        logger.error("Error in goals_assist: %s", exc, exc_info=True)
        return 500, {
            "error": "GOAL_MAKER_ERROR",
            "message": str(exc),
            "timestamp": datetime.now(),
        }


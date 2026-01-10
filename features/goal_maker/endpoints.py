"""Goal Maker Agent endpoints."""

import json
import logging
from django.utils import timezone

from ninja import Router
from django.db import transaction

from features.goal_maker.agent import Goal_maker_agent
from features.orchestrator.schemas import (
    GoalMakerRequestSchema,
    GoalMakerResponseSchema,
)
from features.crud.users.service import get_user_summary
from features.crud.conversations.service import (
    get_conversation_summary,
    insert_chat_message,
)
from core.models import ChatConversation

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.post("/assist", response=GoalMakerResponseSchema)
def goals_assist(request, payload: GoalMakerRequestSchema):
    """
    Manages its own chat history subset or links to main conversation.
    """
    user_id = request.user.id
    conversation_id = payload.conversation_id or 0
    user_request = payload.user_request

    # 1. Fetch Context
    user_summary = get_user_summary(user_id)
    conversation_summary = (
        get_conversation_summary(conversation_id, limit=10)
        if conversation_id
        else "No history."
    )

    # 2. Invoke Agent
    try:
        goal_result = Goal_maker_agent.invoke(
            {
                "user_info": user_summary,
                "user_request": user_request,
                "last_conversation": conversation_summary,
                "current_date": timezone.now().strftime("%Y-%m-%d"),
            }
        )
    except Exception as e:
        logger.exception("Goal Maker Agent failed")
        return {
            "conversation_id": conversation_id,
            "message": f"Error interacting with Goal Maker: {str(e)}",
            "is_done": True,
        }

    if goal_result is None:
        logger.error("Goal Maker Agent returned None")
        return {
            "conversation_id": conversation_id,
            "message": "The Goal Maker agent could not generate a valid response (returned None).",
            "is_done": True,
        }

    # 3. Store interaction using Django ORM
    if conversation_id:
        try:
            with transaction.atomic():
                # User Msg
                insert_chat_message(
                    conversation_id=conversation_id,
                    sender_type="user",
                    source_agent="User",
                    content=user_request,
                )
                # Assistant Msg
                insert_chat_message(
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="GoalMaker",
                    content=goal_result.message,
                )

                # Structured Payload (if any)
                goal_payload = {
                    "goal_name": goal_result.goal_name,
                    "target": goal_result.target,
                    "goal_description": goal_result.goal_description,
                    "due_date": goal_result.due_date,
                    "plan": goal_result.plan,
                }
                # Only insert if there's meaningful data
                if any(goal_payload.values()):
                    insert_chat_message(
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        source_agent="GoalMaker",
                        content=json.dumps(goal_payload),
                        content_type="json",
                    )

                # Update conversation timestamp
                ChatConversation.objects.filter(id=conversation_id).update(
                    last_message_at=timezone.now()
                )
        except Exception:
            logger.exception("Failed to store GoalMaker interaction")

    return {
        "conversation_id": conversation_id,
        "message": goal_result.message,
        "goal_name": goal_result.goal_name,
        "target": goal_result.target,
        "goal_description": goal_result.goal_description,
        "due_date": goal_result.due_date,
        "plan": goal_result.plan,
        "is_done": goal_result.is_done,
    }

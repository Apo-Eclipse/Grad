"""Goal Maker Agent endpoints."""
import json
import logging
from datetime import datetime

from ninja import Router
from django.db import connection

from agents.goal_maker import Goal_maker_agent
from ..assistants.maker_schemas import GoalMakerRequestSchema, GoalMakerResponseSchema
from ..assistants.helpers import get_user_summary, get_conversation_summary, _insert_chat_message

logger = logging.getLogger(__name__)
router = Router()


@router.post("/assist", response=GoalMakerResponseSchema)
def goals_assist(request, payload: GoalMakerRequestSchema):
    """
    Direct endpoint for the Goal Maker Agent.
    Manages its own chat history subset or links to main conversation.
    """
    user_id = payload.user_id
    conversation_id = payload.conversation_id or 0
    user_request = payload.user_request

    # 1. Fetch Context
    user_summary = get_user_summary(user_id)
    conversation_summary = get_conversation_summary(
        conversation_id, limit=10
    ) if conversation_id else "No history."

    # 2. Invoke Agent
    try:
        goal_result = Goal_maker_agent.invoke(
            {
                "user_info": user_summary,
                "user_request": user_request,
                "last_conversation": conversation_summary,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
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

    # 3. Store interaction (optional but recommended if we want persistence)
    # The original api.py implementation did manual insertion.
    if conversation_id:
        try:
            with connection.cursor() as cursor:
                now = datetime.now()
                # User Msg
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="user",
                    source_agent="User",
                    content=user_request,
                    created_at=now,
                )
                # Assistant Msg
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="GoalMaker",
                    content=goal_result.message,
                    created_at=now,
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
                    _insert_chat_message(
                        cursor,
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        source_agent="GoalMaker",
                        content=json.dumps(goal_payload),
                        content_type="json",
                        created_at=now,
                    )
                    
                connection.commit()
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

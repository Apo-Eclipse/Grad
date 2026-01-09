"""Budget Maker Agent endpoints."""

import json
import logging
from datetime import datetime

from ninja import Router
from django.db import transaction

from agents.budget_maker import Budget_maker_agent
from ..assistants.maker_schemas import (
    BudgetMakerRequestSchema,
    BudgetMakerResponseSchema,
)
from ..assistants.helpers import (
    get_user_summary,
    get_conversation_summary,
    _insert_chat_message,
)
from ..models import ChatConversation

logger = logging.getLogger(__name__)
router = Router()


@router.post("/assist", response=BudgetMakerResponseSchema)
def budget_assist(request, payload: BudgetMakerRequestSchema):
    """
    Direct endpoint for the Budget Maker Agent.
    """
    user_id = payload.user_id
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
        budget_result = Budget_maker_agent.invoke(
            {
                "user_info": user_summary,
                "user_request": user_request,
                "last_conversation": conversation_summary,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
            }
        )
    except Exception as e:
        logger.exception("Budget Maker Agent failed")
        return {
            "conversation_id": conversation_id,
            "message": f"Error interacting with Budget Maker: {str(e)}",
            "is_done": True,
        }

    # 3. Store interaction using Django ORM
    if conversation_id:
        try:
            with transaction.atomic():
                # User Msg
                _insert_chat_message(
                    conversation_id=conversation_id,
                    sender_type="user",
                    source_agent="User",
                    content=user_request,
                )
                # Assistant Msg
                _insert_chat_message(
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="BudgetMaker",
                    content=budget_result.message,
                )

                # Structured Payload
                budget_payload = {
                    "action": budget_result.action,
                    "budget_name": budget_result.budget_name,
                    "budget_id": budget_result.budget_id,
                    "total_limit": budget_result.total_limit,
                    "description": budget_result.description,
                    "priority_level": budget_result.priority_level_int,
                }

                if any(budget_payload.values()):
                    _insert_chat_message(
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        source_agent="BudgetMaker",
                        content=json.dumps(budget_payload),
                        content_type="json",
                    )

                # Update conversation timestamp
                ChatConversation.objects.filter(id=conversation_id).update(
                    last_message_at=datetime.now()
                )
        except Exception:
            logger.exception("Failed to store BudgetMaker interaction")

    return {
        "conversation_id": conversation_id,
        "message": budget_result.message,
        "action": budget_result.action,
        "budget_name": budget_result.budget_name,
        "budget_id": budget_result.budget_id,
        "total_limit": budget_result.total_limit,
        "description": budget_result.description,
        "priority_level_int": budget_result.priority_level_int,
        "is_done": budget_result.is_done,
    }

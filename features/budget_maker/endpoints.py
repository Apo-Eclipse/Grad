"""Budget Maker Agent endpoints."""

import json
import logging
from django.utils import timezone
from asgiref.sync import sync_to_async

from ninja import Router
from django.db import transaction

from features.budget_maker.agent import Budget_maker_agent
from features.orchestrator.schemas import (
    BudgetMakerRequestSchema,
    BudgetMakerResponseSchema,
)
from features.crud.users.service import get_user_summary
from features.crud.conversations.service import (
    get_conversation_context,
    insert_chat_message,
)
from core.models import ChatConversation

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.post("/assist", response=BudgetMakerResponseSchema)
async def budget_assist(request, payload: BudgetMakerRequestSchema):
    """
    Direct endpoint for the Budget Maker Agent.
    """

    user_id = request.user.id
    conversation_id = payload.conversation_id or 0
    user_request = payload.user_request

    # 1. Fetch Context (sync ORM operations wrapped)
    @sync_to_async
    def fetch_context():
        user_summary = get_user_summary(user_id)
        if conversation_id:
            context = get_conversation_context(conversation_id, limit=10)
            conversation_history = context["history"]
            current_state = context["current_state"]
        else:
            conversation_history = "No history."
            current_state = None
        return user_summary, conversation_history, current_state

    user_summary, conversation_history, current_state = await fetch_context()

    # 2. Invoke Agent using native async (.ainvoke)
    try:
        budget_result = await Budget_maker_agent.ainvoke(
            {
                "user_info": user_summary,
                "user_request": user_request,
                "last_conversation": conversation_history,
                "current_budget_state": current_state or "No budget in progress.",
                "current_date": timezone.now().strftime("%Y-%m-%d"),
            }
        )
    except Exception as e:
        logger.exception("Budget Maker Agent failed")
        return {
            "conversation_id": conversation_id,
            "message": f"Error interacting with Budget Maker: {str(e)}",
            "is_done": True,
        }

    if budget_result is None:
        logger.error("Budget Maker Agent returned None")
        return {
            "conversation_id": conversation_id,
            "message": "I apologize, but I encountered an internal error while processing your request. Please try again.",
            "is_done": True,
        }

    # 3. Store interaction using Django ORM
    @sync_to_async
    def store_interaction():
        if not conversation_id:
            return
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
                    insert_chat_message(
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        source_agent="BudgetMaker",
                        content=json.dumps(budget_payload),
                        content_type="json",
                    )

                # Update conversation timestamp
                ChatConversation.objects.filter(id=conversation_id).update(
                    last_message_at=timezone.now()
                )
        except Exception:
            logger.exception("Failed to store BudgetMaker interaction")

    await store_interaction()

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

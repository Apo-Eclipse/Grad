"""Transaction Maker Agent endpoints."""

import json
import logging
from django.utils import timezone

from ninja import Router
from django.db import transaction

from features.transaction_maker.agent import Transaction_maker_agent
from features.orchestrator.schemas import (
    TransactionMakerRequestSchema,
    TransactionMakerResponseSchema,
)
from features.crud.conversations.service import (
    get_conversation_summary,
    insert_chat_message,
)
from features.crud.budgets.service import fetch_active_budgets
from core.models import ChatConversation

logger = logging.getLogger(__name__)
router = Router()


@router.post("/assist", response=TransactionMakerResponseSchema)
def transaction_assist(request, payload: TransactionMakerRequestSchema):
    """
    Direct endpoint for the Transaction Maker Agent.
    """
    user_id = payload.user_id
    conversation_id = payload.conversation_id or 0
    user_request = payload.user_request

    # 1. Fetch Context
    conversation_summary = (
        get_conversation_summary(conversation_id, limit=10)
        if conversation_id
        else "No history."
    )

    active_budgets = fetch_active_budgets(user_id)
    # Format budgets for prompt
    budgets_str = (
        "\n".join([f"- {b['budget_name']} (ID: {b['id']})" for b in active_budgets])
        if active_budgets
        else "No active budgets."
    )

    # 2. Invoke Agent
    try:
        txn_result = Transaction_maker_agent.invoke(
            {
                "user_request": user_request,
                "last_conversation": conversation_summary,
                "active_budgets": budgets_str,
                "current_date": timezone.now().strftime("%Y-%m-%d"),
            }
        )
    except Exception as e:
        logger.exception("Transaction Maker Agent failed")
        return {
            "conversation_id": conversation_id,
            "message": f"Error interacting with Transaction Maker: {str(e)}",
            "is_done": True,
        }

    if txn_result is None:
        logger.error("Transaction Maker Agent returned None")
        return {
            "conversation_id": conversation_id,
            "message": "The Transaction Maker agent could not generate a valid response (returned None).",
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
                    source_agent="TransactionMaker",
                    content=txn_result.message,
                )

                # Structured Payload
                txn_payload = {
                    "amount": txn_result.amount,
                    "budget_id": txn_result.budget_id,
                    "store_name": txn_result.store_name,
                    "date": txn_result.date,
                    "time": txn_result.time,
                    "city": txn_result.city,
                    "neighbourhood": txn_result.neighbourhood,
                    "type_spending": txn_result.type_spending,
                }

                if any(txn_payload.values()):
                    insert_chat_message(
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        source_agent="TransactionMaker",
                        content=json.dumps(txn_payload),
                        content_type="json",
                    )

                # Update conversation timestamp
                ChatConversation.objects.filter(id=conversation_id).update(
                    last_message_at=timezone.now()
                )
        except Exception:
            logger.exception("Failed to store TransactionMaker interaction")

    return {
        "conversation_id": conversation_id,
        "message": txn_result.message,
        "amount": txn_result.amount,
        "budget_id": txn_result.budget_id,
        "store_name": txn_result.store_name,
        "date": txn_result.date,
        "time": txn_result.time,
        "city": txn_result.city,
        "neighbourhood": txn_result.neighbourhood,
        "type_spending": txn_result.type_spending,
        "is_done": txn_result.is_done,
    }

"""Transaction Maker API endpoints."""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from ninja import Router
from django.db import connection

from personal_assistant_api.assistants.maker_schemas import (
    TransactionMakerRequestSchema,
    TransactionMakerResponseSchema,
)
from personal_assistant_api.assistants.schemas import AnalysisErrorSchema
from personal_assistant_api.assistants.helpers import (
    get_conversation_summary,
    fetch_active_budgets,
)
from agents.transaction_maker import Transaction_maker_agent

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


@router.post("/assist", response={200: TransactionMakerResponseSchema, 400: AnalysisErrorSchema, 500: AnalysisErrorSchema})
def transaction_assist(request, payload: TransactionMakerRequestSchema):
    """
    Handle a transaction-making conversation with memory using the Transaction Maker agent.
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

        # Build context for the agent
        # Fetch active budgets and format them
        active_budgets_list = fetch_active_budgets(payload.user_id)
        active_budgets_str = ", ".join(
            [f"{b['budget_name']} (ID: {b['budget_id']})" for b in active_budgets_list]
        ) if active_budgets_list else "No active budgets found."

        # Fetch conversation history
        last_conversation = get_conversation_summary(conversation_id)

        agent_input = {
            "active_budgets": active_budgets_str,
            "current_date": datetime.now().date().isoformat(),
            "last_conversation": last_conversation,
            "user_request": payload.user_request,
        }

        transaction_result = Transaction_maker_agent.invoke(agent_input)

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

            # TransactionMaker reply
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent="TransactionMaker",
                content=transaction_result.message,
                created_at=now,
            )

            # Optional structured transaction payload
            transaction_payload: Dict[str, Any] = {
                "amount": transaction_result.amount,
                "budget_id": transaction_result.budget_id,
                "store_name": transaction_result.store_name,
                "date": transaction_result.date,
                "time": transaction_result.time,
                "city": transaction_result.city,
                "neighbourhood": transaction_result.neighbourhood,
                "type_spending": transaction_result.type_spending,
                "is_done": transaction_result.is_done,
            }
            if any(transaction_payload.values()):
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="TransactionMaker",
                    content=json.dumps(transaction_payload),
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
            "message": transaction_result.message,
            "amount": transaction_result.amount,
            "budget_id": transaction_result.budget_id,
            "store_name": transaction_result.store_name,
            "date": transaction_result.date,
            "time": transaction_result.time,
            "city": transaction_result.city,
            "neighbourhood": transaction_result.neighbourhood,
            "type_spending": transaction_result.type_spending,
            "is_done": transaction_result.is_done,
        }
        return 200, response

    except Exception as exc:
        logger.error("Error in transaction_assist: %s", exc, exc_info=True)
        return 500, {
            "error": "TRANSACTION_MAKER_ERROR",
            "message": str(exc),
            "timestamp": datetime.now(),
        }


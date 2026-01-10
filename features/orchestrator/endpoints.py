"""Main Personal Assistant API endpoints."""

import json
import logging
from django.utils import timezone
from typing import Any, Dict, Optional

from ninja import Router
from django.db import transaction

from features.orchestrator.schemas import (
    AnalysisRequestSchema,
    AnalysisResponseSchema,
)
from features.crud.conversations.service import insert_chat_message
from core.models import ChatConversation
from features.orchestrator.graph import main_orchestrator_graph
from asgiref.sync import sync_to_async

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


def _store_messages_sync(
    conversation_id: int,
    user_query: str,
    assistant_output: str,
    data: Optional[Dict[str, Any]],
    agents_used: Optional[str] = None,
) -> bool:
    """Synchronous database operation to store messages for the main assistant."""
    if agents_used is None:
        agents_used = ""

    try:
        with transaction.atomic():
            # User message
            insert_chat_message(
                conversation_id=conversation_id,
                sender_type="user",
                source_agent="User",
                content=user_query,
            )

            # Determine source agent label
            agent_source_map = {
                "behaviour_analyst": "BehaviourAnalyst",
                "database_agent": "DatabaseAgent",
            }
            source_agent = agent_source_map.get(agents_used, "PersonalAssistant")

            # Assistant message
            insert_chat_message(
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent=source_agent,
                content=assistant_output,
            )

            # Optional data payload
            if data:
                insert_chat_message(
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="DatabaseAgent",
                    content=json.dumps(data),
                    content_type="json",
                )

            # Update conversation timestamp
            ChatConversation.objects.filter(id=conversation_id).update(
                last_message_at=timezone.now()
            )

            return True

    except Exception as exc:
        logger.warning("Could not store messages: %s", exc)
        return False


@router.post("/analyze", response=AnalysisResponseSchema)
async def analyze(request, payload: AnalysisRequestSchema):
    """
    Primary endpoint: Analyze a user request via LangGraph agents.
    Logs the conversation and returns the answer.
    """
    # 1. Prepare State for Graph
    metadata = payload.metadata or {}
    if payload.conversation_id:
        metadata["conversation_id"] = payload.conversation_id

    # Always use authenticated user_id
    current_user_id = request.user.id
    metadata["user_id"] = current_user_id

    initial_state = {
        "messages": [("user", payload.query)],
        "user_message": payload.query,
        "user_id": current_user_id,
        "conversation_id": metadata.get("conversation_id"),
        "filters": payload.filters or {},
    }

    try:
        # 2. Invoke Graph
        result = await main_orchestrator_graph.ainvoke(initial_state)

        # 3. Extract Results
        final_output = result.get("final_output", "No response generated.")
        data = result.get("data")

        # 4. Store Conversation (Sync wrapper)
        if payload.conversation_id:
            await sync_to_async(_store_messages_sync)(
                conversation_id=payload.conversation_id,
                user_query=payload.query,
                assistant_output=final_output,
                data=data,
                agents_used=result.get("agents_used"),
            )

        return {
            "final_output": final_output,
            "data": data,
            "conversation_id": payload.conversation_id,
        }

    except Exception as exc:
        logger.exception("Orchestrator failed")
        return {
            "final_output": f"I encountered an error processing your request: {exc}",
            "data": None,
            "conversation_id": payload.conversation_id,
        }


@router.get("/health")
def health(request):
    """Health check endpoint."""
    return {"status": "healthy", "service": "PersonalAssistantAPI"}

"""Main Personal Assistant API endpoints."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ninja import Router
from django.db import connection

from .schemas import (
    AnalysisRequestSchema, 
    AnalysisResponseSchema,
    ConversationStartSchema,
    ConversationResponseSchema
)
from .helpers import _insert_chat_message
from graphs.main_graph import main_orchestrator_graph
from ..core.database import execute_modify_returning
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
router = Router()


def _store_messages_sync(
    conversation_id: int,
    user_query: str,
    assistant_output: str,
    data: Optional[Dict[str, Any]],
    agents_used: Optional[str] = None,) -> bool:
    """Synchronous database operation to store messages for the main assistant."""
    if agents_used is None:
        agents_used = ""

    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            # User message
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="user",
                source_agent="User",
                content=user_query,
                created_at=now,
            )

            # Determine source agent label
            agent_source_map = {
                "behaviour_analyst": "BehaviourAnalyst",
                "database_agent": "DatabaseAgent",
            }
            source_agent = agent_source_map.get(agents_used, "PersonalAssistant")
            
            # Assistant message
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent=source_agent,
                content=assistant_output,
                created_at=now,
            )

            # Optional data payload
            if data:
                _insert_chat_message(
                    cursor,
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    source_agent="DatabaseAgent",
                    content=json.dumps(data),
                    content_type="json",
                    created_at=now,
                )

            # Update conversation timestamp
            cursor.execute(
                """
                UPDATE chat_conversations SET last_message_at = %s WHERE conversation_id = %s
                """,
                [now, conversation_id],
            )
            connection.commit()
            return True
            
    except Exception as exc:
        logger.warning("Could not store messages: %s", exc)
        try:
            connection.rollback()
        except Exception:
            pass
        return False


@router.post("/conversations/start", response=ConversationResponseSchema)
def start_conversation(request, payload: ConversationStartSchema):
    """Start a new conversation thread."""
    query = """
        INSERT INTO chat_conversations (user_id, channel, started_at, last_message_at)
        VALUES (%s, %s, NOW(), NOW())
        RETURNING conversation_id, user_id, channel, started_at
    """
    success, _, row = execute_modify_returning(
        query, 
        [payload.user_id, payload.channel], 
        log_name="start_conversation"
    )
    if not success or not row:
        # Fallback or error
        raise Exception("Failed to start conversation")
        
    return row


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
    if payload.user_id:
        metadata["user_id"] = payload.user_id

    initial_state = {
        "messages": [("user", payload.query)],
        "user_message": payload.query,
        "user_id": metadata.get("user_id"),
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
                agents_used=result.get("agents_used") 
            )

        return {
            "final_output": final_output,
            "data": data,
            "conversation_id": payload.conversation_id
        }

    except Exception as exc:
        logger.exception("Orchestrator failed")
        return {
            "final_output": f"I encountered an error processing your request: {exc}",
            "data": None,
            "conversation_id": payload.conversation_id
        }


@router.get("/health")
def health(request):
    """Health check endpoint."""
    return {"status": "healthy", "service": "PersonalAssistantAPI"}

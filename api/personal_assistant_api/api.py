"""
API endpoints for the Personal Assistant.
"""
import logging
import json
from typing import Dict, Any
from datetime import datetime
from ninja import Router
from django.db import connection
from asgiref.sync import sync_to_async

from .schemas import AnalysisRequestSchema, AnalysisErrorSchema, ConversationStartSchema, ConversationResponseSchema
from .services import get_analyst_service

logger = logging.getLogger(__name__)
router = Router()
analyst_service = get_analyst_service()


def _insert_chat_message(
    cursor,
    *,
    conversation_id,
    sender_type,
    source_agent,
    content,
    content_type="text",
    language="en",
    created_at,
):
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


def _store_messages_sync(conversation_id, user_query, assistant_output, data, agents_used=None):
    """Synchronous database operation to store messages."""
    if agents_used is None:
        agents_used = ""
    
    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="user",
                source_agent="User",
                content=user_query,
                created_at=now,
            )

            agent_source_map = {
                "behaviour_analyst": "BehaviourAnalyst",
                "database_agent": "DatabaseAgent",
            }
            source_agent = agent_source_map.get(agents_used, "PersonalAssistant")
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent=source_agent,
                content=assistant_output,
                created_at=now,
            )

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
            
            # Update conversation last_message_at
            cursor.execute("""
                UPDATE chat_conversations SET last_message_at = %s WHERE conversation_id = %s
            """, [now, conversation_id])
            
            connection.commit()
            return True
    except Exception as e:
        logger.warning(f"Could not store messages: {str(e)}")
        try:
            connection.rollback()
        except:
            pass
        return False


@router.post("conversations/start", response={200: ConversationResponseSchema, 400: AnalysisErrorSchema})
def start_conversation(request, payload: ConversationStartSchema):
    """Start a new conversation and return conversation ID."""
    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            cursor.execute("""
                INSERT INTO chat_conversations (user_id, channel, started_at, last_message_at)
                VALUES (%s, %s, %s, %s)
                RETURNING conversation_id
            """, [payload.user_id, payload.channel, now, now])
            
            result = cursor.fetchone()
            conversation_id = result[0] if result else None
            
            return 200, {
                "conversation_id": conversation_id,
                "user_id": payload.user_id,
                "channel": payload.channel,
                "started_at": now
            }
    
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}", exc_info=True)
        return 400, {"error": "CONVERSATION_ERROR", "message": str(e), "timestamp": datetime.now()}


@router.post("analyze", response={200: Dict[str, Any], 400: AnalysisErrorSchema, 500: AnalysisErrorSchema})
async def analyze(request, payload: AnalysisRequestSchema):
    """Submit request and get results synchronously. Stores message in conversation."""
    try:
        if not payload.query or not payload.query.strip():
            return 400, {"error": "INVALID_QUERY", "message": "Query cannot be empty", "timestamp": datetime.now()}
        
        logger.info(f"Analyzing: {payload.query}")
        
        # Prepare metadata with conversation_id included
        metadata = {
            **(payload.metadata or {}),
            "conversation_id": payload.conversation_id,
            "user_id": payload.user_id,
        }
        
        result = await analyst_service.run_analysis(
            query=payload.query,
            filters=payload.filters,
            metadata=metadata,
        )
        
        final_output = result.get("final_output") or result.get("message") or ""
        data = result.get("data")
        agents_used = result.get("agents_used", "")
        conversation_id = payload.conversation_id
        
        if conversation_id:
            await sync_to_async(_store_messages_sync)(
                conversation_id=conversation_id,
                user_query=payload.query,
                assistant_output=final_output,
                data=data,
                agents_used=agents_used,
            )
        
        response = {"final_output": final_output}
        if data is not None and (not isinstance(data, list) or len(data) > 0):
            response["data"] = data
        if conversation_id:
            response["conversation_id"] = conversation_id
        
        return 200, response
    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 500, {"error": "ANALYSIS_ERROR", "message": str(e), "timestamp": datetime.now()}


@router.get("health", response={200: dict})
def health(request):
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


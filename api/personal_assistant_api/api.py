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


def _store_messages_sync(conversation_id, user_query, assistant_output, data, agents_used=None):
    """Synchronous database operation to store messages."""
    if agents_used is None:
        agents_used = ""
    
    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            
            # Store user message
            cursor.execute("""
                INSERT INTO chat_messages (conversation_id, sender_type, source_agent, content, content_type, language, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [conversation_id, "user", "User", user_query, "text", "en", now])
            
            # Store agent messages if they were used
            if agents_used == "behaviour_analyst":
                cursor.execute("""
                    INSERT INTO chat_messages (conversation_id, sender_type, source_agent, content, content_type, language, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [conversation_id, "assistant", "BehaviourAnalyst", assistant_output, "text", "en", now])
            elif agents_used == "database_agent":
                # For database agent, store both the result data and response
                cursor.execute("""
                    INSERT INTO chat_messages (conversation_id, sender_type, source_agent, content, content_type, language, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [conversation_id, "assistant", "DatabaseAgent", assistant_output, "text", "en", now])
            else:
                # General conversation
                cursor.execute("""
                    INSERT INTO chat_messages (conversation_id, sender_type, source_agent, content, content_type, language, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [conversation_id, "assistant", "PersonalAssistant", assistant_output, "text", "en", now])
            
            # If data exists, store it as a separate message (original behavior for data persistence)
            if data:
                cursor.execute("""
                    INSERT INTO chat_messages (conversation_id, sender_type, source_agent, content, content_type, language, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [conversation_id, "assistant", "DatabaseAgent", json.dumps(data), "json", "en", now])
            
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
        metadata = payload.metadata or {}
        metadata["conversation_id"] = payload.conversation_id
        metadata["user_id"] = payload.user_id
        
        result = await analyst_service.run_analysis(query=payload.query, filters=payload.filters, metadata=metadata)
        
        # Extract final_output, data, and agents_used from result
        final_output = result.get("final_output") or result.get("message") or ""
        data = result.get("data")
        agents_used = result.get("agents_used", "")
        
        # Get conversation_id
        conversation_id = payload.conversation_id
        
        # Always store messages if conversation_id exists
        if conversation_id:
            # Use sync_to_async to run database operations in thread pool
            await sync_to_async(_store_messages_sync)(
                conversation_id=conversation_id,
                user_query=payload.query,
                assistant_output=final_output,
                data=data,
                agents_used=agents_used
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


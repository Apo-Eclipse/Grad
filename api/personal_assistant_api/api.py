"""
API endpoints for the Personal Assistant.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ninja import Router
from django.db import connection
from asgiref.sync import sync_to_async

from .schemas import (
    AnalysisRequestSchema,
    AnalysisErrorSchema,
    ConversationStartSchema,
    ConversationResponseSchema,
    GoalMakerRequestSchema,
    GoalMakerResponseSchema,
)
from .services import get_analyst_service
from agents.goal_maker import Goal_maker_agent

logger = logging.getLogger(__name__)
router = Router()
analyst_service = get_analyst_service()


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


def _get_user_summary(user_id: int) -> str:
    """
    Fetch a brief user summary string tuned for goal-making.

    Pulls core profile information plus lightweight income/goal context so the
    Goal Maker agent can judge whether a goal is realistic and relevant.
    """
    try:
        with connection.cursor() as cursor:
            # Basic user profile
            cursor.execute(
                """
                SELECT
                    first_name,
                    last_name,
                    job_title,
                    address,
                    employment_status,
                    education_level,
                    birthday
                FROM users
                WHERE user_id = %s
            """,
                [user_id],
            )
            row = cursor.fetchone()
            if not row:
                return f"User {user_id} (no profile found)."

            (
                first_name,
                last_name,
                job_title,
                address,
                employment_status,
                education_level,
                birthday,
            ) = row

            # Aggregate income across all sources
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total_income
                FROM income
                WHERE user_id = %s
            """,
                [user_id],
            )
            income_row = cursor.fetchone() or (0,)
            total_income = float(income_row[0] or 0)

            # Retrieve all active goals with full details
            cursor.execute(
                """
                SELECT
                    goal_id,
                    goal_name,
                    description,
                    target,
                    start_date,
                    due_date,
                    status
                FROM goals
                WHERE user_id = %s
                  AND (status IS NULL OR status = 'active')
                ORDER BY due_date ASC
            """,
                [user_id],
            )
            active_goals_rows = cursor.fetchall() or []
            active_goals_count = len(active_goals_rows)

            # Recent spending patterns (last 90 days)
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(amount), 0) AS total_spent_90d
                FROM transactions
                WHERE user_id = %s
                  AND date >= CURRENT_DATE - INTERVAL '90 days'
            """,
                [user_id],
            )
            spend_row = cursor.fetchone() or (0,)
            total_spent_90d = float(spend_row[0] or 0)

            # Top 3 spending categories (type_spending) in last 90 days
            cursor.execute(
                """
                SELECT
                    type_spending,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s
                  AND date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY type_spending
                ORDER BY total DESC
                LIMIT 3
            """,
                [user_id],
            )
            top_categories_rows = cursor.fetchall() or []

            # Top 3 stores in last 90 days
            cursor.execute(
                """
                SELECT
                    store_name,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s
                  AND date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY store_name
                ORDER BY total DESC
                LIMIT 3
            """,
                [user_id],
            )
            top_stores_rows = cursor.fetchall() or []

            # Top city / neighbourhood in last 90 days
            cursor.execute(
                """
                SELECT
                    city,
                    neighbourhood,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s
                  AND date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY city, neighbourhood
                ORDER BY total DESC
                LIMIT 1
            """,
                [user_id],
            )
            top_area_row = cursor.fetchone()

        name = " ".join(part for part in [first_name, last_name] if part)
        parts: List[str] = []

        if name:
            parts.append(f"Name: {name}")
        parts.append(f"User ID: {user_id}")

        if job_title:
            parts.append(f"Job title: {job_title}")
        if employment_status:
            parts.append(f"Employment status: {employment_status}")
        if education_level:
            parts.append(f"Education level: {education_level}")
        if address:
            parts.append(f"Address: {address}")
        if birthday:
            parts.append(f"Birthday: {birthday}")

        parts.append(f"Total recorded income (all sources): {total_income:.2f} EGP")
        if total_spent_90d > 0:
            parts.append(f"Total spending over last 90 days: {total_spent_90d:.2f} EGP")

        if active_goals_count > 0:
            goal_bits = [f"{active_goals_count} active goal(s):"]
            for goal_id, goal_name, description, target, start_date, due_date, status in active_goals_rows:
                goal_line = f"  - {goal_name}"
                if description:
                    goal_line += f" ({description})"
                if target:
                    goal_line += f" | Target: {float(target):.2f} EGP"
                if start_date:
                    goal_line += f" | Start: {start_date}"
                if due_date:
                    goal_line += f" | Due: {due_date}"
                goal_bits.append(goal_line)
            parts.append("Active goals: " + "; ".join(goal_bits))
        else:
            parts.append("Active goals: no active goals recorded yet")

        if top_categories_rows:
            categories_str = ", ".join(
                f"{name} ({float(total):.0f} EGP)"
                for name, total in top_categories_rows
                if name
            )
            if categories_str:
                parts.append(f"Top categories last 90 days: {categories_str}")

        if top_stores_rows:
            stores_str = ", ".join(
                f"{name} ({float(total):.0f} EGP)"
                for name, total in top_stores_rows
                if name
            )
            if stores_str:
                parts.append(f"Top stores last 90 days: {stores_str}")

        if top_area_row:
            city, neighbourhood, area_total = top_area_row
            area_bits = []
            if city:
                area_bits.append(str(city))
            if neighbourhood:
                area_bits.append(str(neighbourhood))
            if area_bits:
                parts.append(
                    f"Main spending area last 90 days: "
                    f"{' - '.join(area_bits)} ({float(area_total or 0):.0f} EGP)"
                )

        return "; ".join(parts)
    except Exception as exc:
        logger.warning("Failed to load user summary for %s: %s", user_id, exc)
        return f"User {user_id}."


def _get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
    """Return a simple textual summary of the last N messages for a conversation."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sender_type, source_agent, content, content_type
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT %s
            """,
                [conversation_id, limit],
            )
            rows = cursor.fetchall()

        if not rows:
            return "No previous messages in this conversation."

        lines: List[str] = []
        for idx, (sender_type, source_agent, content, content_type) in enumerate(rows, start=1):
            if content_type == "json":
                continue
            sender_label = source_agent or sender_type or "Unknown"
            lines.append(f"{idx}. [{sender_label}] {content}")
        return "\n".join(lines) if lines else "No previous text messages in this conversation."
    except Exception as exc:
        logger.warning("Failed to load conversation summary for %s: %s", conversation_id, exc)
        return "No previous messages (error while loading history)."


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


@router.post("goals/assist", response={200: GoalMakerResponseSchema, 400: AnalysisErrorSchema, 500: AnalysisErrorSchema})
def goals_assist(request, payload: GoalMakerRequestSchema):
    """
    Handle a goal-making conversation with memory using the Goal Maker agent.

    - Creates a new conversation when conversation_id is not provided.
    - Reuses existing chat_conversations / chat_messages for memory.
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

        # Build memory context for the agent
        user_info = _get_user_summary(payload.user_id)
        last_conversation = _get_conversation_summary(conversation_id)

        agent_input = {
            "user_info": user_info,
            "last_conversation": last_conversation,
            "current_date": datetime.now().date().isoformat(),
            "user_request": payload.user_request,
        }

        goal_result = Goal_maker_agent.invoke(agent_input)

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

            # GoalMaker reply
            _insert_chat_message(
                cursor,
                conversation_id=conversation_id,
                sender_type="assistant",
                source_agent="GoalMaker",
                content=goal_result.message,
                created_at=now,
            )

            # Optional structured goal payload
            goal_payload: Dict[str, Any] = {
                "goal_name": goal_result.goal_name,
                "target": goal_result.target,
                "goal_description": goal_result.goal_description,
                "due_date": goal_result.due_date,
            }
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
            "message": goal_result.message,
            "goal_name": goal_result.goal_name,
            "target": goal_result.target,
            "goal_description": goal_result.goal_description,
            "due_date": goal_result.due_date,
            "is_done": getattr(goal_result, "is_done", False),
        }
        return 200, response

    except Exception as exc:
        logger.error("Error in goals_assist: %s", exc, exc_info=True)
        return 500, {
            "error": "GOAL_MAKER_ERROR",
            "message": str(exc),
            "timestamp": datetime.now(),
        }


@router.get("health", response={200: dict})
def health(request):
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

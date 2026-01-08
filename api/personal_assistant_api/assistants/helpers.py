"""Helper functions for assistants."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import connection

from ..core.database import run_select, run_select_single, execute_modify

logger = logging.getLogger(__name__)


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


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active budgets for a user."""
    query = """
        SELECT
            budget_id,
            budget_name,
            total_limit,
            priority_level_int
        FROM budget
        WHERE user_id = %s
          AND is_active = true
        ORDER BY priority_level_int DESC
    """
    return run_select(query, [user_id], log_name="fetch_active_budgets")


def get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
    """
    Retrieve the last N messages formatted as 'Sender: Content'.
    Useful for LLM memory context.
    """
    try:
        with connection.cursor() as cursor:
            # We want the *latest* N messages, but in chronological order.
            # So we fetch in DESC order with limit, then reverse in Python (or use CTE).
            cursor.execute(
                """
                SELECT sender_type, source_agent, content, content_type
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY message_id ASC
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
            
            # Label by source_agent if possible, else sender_type
            sender_label = source_agent or sender_type or "Unknown"
            
            lines.append(f"{idx}. [{sender_label}] {content}")

        return "\n".join(lines) if lines else "No previous text messages in this conversation."

    except Exception as exc:
        logger.warning("Failed to load conversation summary for %s: %s", conversation_id, exc)
        return "No previous messages (error while loading history)."


def get_user_summary(user_id: int) -> str:
    """
    Fetch a brief user summary string tuned for goal-making/budgeting.
    Includes profile, income, active goals, active budgets, and recent spending.
    """
    try:
        # Basic user profile
        user_query = """
            SELECT first_name, last_name, job_title, address, employment_status, education_level
            FROM users WHERE user_id = %s
        """
        user_row = run_select_single(user_query, [user_id], log_name="user_summary_profile")
        
        if not user_row:
            return f"User {user_id} (no profile found)."

        # Income
        inc_query = "SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = %s"
        inc_row = run_select_single(inc_query, [user_id], log_name="user_summary_income")
        total_income = float(inc_row["total"]) if inc_row else 0.0

        # Goals (active)
        goals_query = """
            SELECT goal_name, target, due_date
            FROM goals
            WHERE user_id = %s AND (status IS NULL OR status = 'active')
            ORDER BY due_date ASC
        """
        goals_rows = run_select(goals_query, [user_id], log_name="user_summary_goals")

        # Active Budgets
        budgets_rows = fetch_active_budgets(user_id)

        # Spending (90d)
        spend_query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '90 days'
        """
        spend_row = run_select_single(spend_query, [user_id], log_name="user_summary_spend")
        total_spent_90d = float(spend_row["total"]) if spend_row else 0.0

        # Top Categories
        cat_query = """
            SELECT type_spending, SUM(amount) as total
            FROM transactions
            WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY type_spending ORDER BY total DESC LIMIT 3
        """
        top_cats = run_select(cat_query, [user_id], log_name="user_summary_cats")

        # Top Stores
        store_query = """
            SELECT store_name, SUM(amount) as total
            FROM transactions
            WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY store_name ORDER BY total DESC LIMIT 3
        """
        top_stores = run_select(store_query, [user_id], log_name="user_summary_stores")

        # Formatting
        name = f"{user_row['first_name']} {user_row['last_name']}"
        parts = [
            f"Name: {name}",
            f"User ID: {user_id}",
            f"Job: {user_row.get('job_title', 'N/A')}",
            f"Employment: {user_row.get('employment_status', 'N/A')}",
            f"Income (Monthly approx): {total_income:.2f}",
        ]

        if goals_rows:
            goal_strs = [f"- {g['goal_name']} (Target: {float(g['target'] or 0):.2f})" for g in goals_rows]
            parts.append("Active Goals: " + "; ".join(goal_strs))
        else:
            parts.append("Active Goals: None")
            
        if budgets_rows:
            budget_strs = [f"- {b['budget_name']} (ID: {b['budget_id']}, Limit: {float(b['total_limit']):.2f})" for b in budgets_rows]
            parts.append("Active Budgets: " + "; ".join(budget_strs))
        else:
            parts.append("Active Budgets: None")

        parts.append(f"Recent Spending (last 90d): {total_spent_90d:.2f}")

        if top_cats:
            cat_strs = [f"{c['type_spending']} ({float(c['total']):.2f})" for c in top_cats]
            parts.append("Top Spending Categories: " + ", ".join(cat_strs))

        if top_stores:
            store_strs = [f"{s['store_name']} ({float(s['total']):.2f})" for s in top_stores]
            parts.append("Top Stores: " + ", ".join(store_strs))

        return "\n".join(parts)

    except Exception as exc:
        logger.warning(f"Error building user summary for {user_id}: {exc}")
        return f"Error retrieving user summary for {user_id}."

"""Helper functions for the Personal Assistant API."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from django.db import connection

logger = logging.getLogger(__name__)


def get_user_summary(user_id: int) -> str:
    """
    Fetch a detailed user summary string for context.

    Pulls core profile information plus income/goal/budget/spending context
    so agents can make informed decisions.
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

            # Retrieve all active budgets
            cursor.execute(
                """
                SELECT
                    budget_name,
                    total_limit,
                    priority_level_int
                FROM budget
                WHERE user_id = %s
                  AND is_active = true
                ORDER BY priority_level_int DESC
            """,
                [user_id],
            )
            active_budgets_rows = cursor.fetchall() or []
            active_budgets_count = len(active_budgets_rows)

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

        # Build summary string
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

        if active_budgets_count > 0:
            budget_bits = [f"{active_budgets_count} active budget(s):"]
            for b_name, b_limit, b_prio in active_budgets_rows:
                budget_bits.append(f"  - {b_name} ({float(b_limit):.2f} EGP, Prio {b_prio})")
            parts.append("Active budgets: " + "; ".join(budget_bits))
        else:
            parts.append("Active budgets: no active budgets recorded yet")

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



def get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
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


def get_recent_conversations(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent conversations for context."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT conversation_id, title, channel, started_at, last_message_at
                FROM chat_conversations
                WHERE user_id = %s
                ORDER BY last_message_at DESC
                LIMIT %s
            """,
                [user_id, limit],
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning("Failed to load recent conversations for %s: %s", user_id, exc)
        return []


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve active user budgets."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    budget_id,
                    budget_name,
                    description,
                    total_limit,
                    priority_level_int,
                    is_active,
                    created_at,
                    updated_at
                FROM budget
                WHERE user_id = %s
                  AND is_active = true
                ORDER BY priority_level_int ASC, budget_name
            """,
                [user_id],
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning("Failed to fetch active budgets for %s: %s", user_id, exc)
        return []


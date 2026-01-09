"""Helper functions for assistants."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.db.models.functions import Coalesce

from ..models import (
    Budget,
    ChatMessage,
    ChatConversation,
    Goal,
    Income,
    Transaction,
    Profile,
)

logger = logging.getLogger(__name__)


def _insert_chat_message(
    conversation_id: int,
    sender_type: str,
    source_agent: str,
    content: str,
    content_type: str = "text",
    language: str = "en",
    created_at: datetime = None,
) -> ChatMessage:
    """Insert a single chat message row using Django ORM."""
    return ChatMessage.objects.create(
        conversation_id=conversation_id,
        sender_type=sender_type,
        source_agent=source_agent,
        content=content,
        content_type=content_type,
        language=language,
    )


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active budgets for a user."""
    budgets = (
        Budget.objects.filter(user_id=user_id, is_active=True)
        .order_by("-priority_level_int")
        .values("id", "budget_name", "total_limit", "priority_level_int")
    )
    return list(budgets)


def get_conversation_summary(conversation_id: int, limit: int = 20) -> str:
    """
    Retrieve the last N messages formatted as 'Sender: Content'.
    Useful for LLM memory context.
    """
    try:
        # Use .values() for faster loading
        messages = (
            ChatMessage.objects.filter(conversation_id=conversation_id)
            .order_by("id")
            .values("content_type", "source_agent", "sender_type", "content")[:limit]
        )

        if not messages:
            return "No previous messages in this conversation."

        lines: List[str] = []
        for idx, msg in enumerate(messages, start=1):
            if msg["content_type"] == "json":
                continue

            # Label by source_agent if possible, else sender_type
            sender_label = msg["source_agent"] or msg["sender_type"] or "Unknown"
            lines.append(f"{idx}. [{sender_label}] {msg['content']}")

        return (
            "\n".join(lines)
            if lines
            else "No previous text messages in this conversation."
        )

    except Exception as exc:
        logger.warning(
            "Failed to load conversation summary for %s: %s", conversation_id, exc
        )
        return "No previous messages (error while loading history)."


def get_user_summary(user_id: int) -> str:
    """
    Fetch a brief user summary string tuned for goal-making/budgeting.
    Includes profile, income, active goals, active budgets, and recent spending.
    """
    try:
        # Basic user profile - use .values() for faster loading
        user_data = (
            User.objects.filter(id=user_id).values("first_name", "last_name").first()
        )

        if not user_data:
            return f"User {user_id} (no profile found)."

        profile_data = (
            Profile.objects.filter(user_id=user_id)
            .values("job_title", "employment_status")
            .first()
        )

        # Income - total amount
        income_total = Income.objects.filter(user_id=user_id).aggregate(
            total=Coalesce(Sum("amount"), 0.0)
        )["total"]
        total_income = float(income_total) if income_total else 0.0

        # Goals (active) - already uses .values()
        goals_rows = list(
            Goal.objects.filter(user_id=user_id)
            .filter(Q(status__isnull=True) | Q(status="active"))
            .order_by("due_date")
            .values("goal_name", "target", "due_date")
        )

        # Active Budgets - already uses .values()
        budgets_rows = fetch_active_budgets(user_id)

        # Spending (90 days)
        from django.utils import timezone
        from datetime import timedelta

        ninety_days_ago = timezone.now().date() - timedelta(days=90)

        spend_total = Transaction.objects.filter(
            user_id=user_id, date__gte=ninety_days_ago
        ).aggregate(total=Coalesce(Sum("amount"), 0.0))["total"]
        total_spent_90d = float(spend_total) if spend_total else 0.0

        # Top Categories (90 days) - already uses .values()
        top_cats = list(
            Transaction.objects.filter(user_id=user_id, date__gte=ninety_days_ago)
            .values("type_spending")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:3]
        )

        # Top Stores (90 days) - already uses .values()
        top_stores = list(
            Transaction.objects.filter(user_id=user_id, date__gte=ninety_days_ago)
            .values("store_name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:3]
        )

        # Formatting
        name = f"{user_data['first_name']} {user_data['last_name']}"
        parts = [
            f"Name: {name}",
            f"User ID: {user_id}",
        ]

        if profile_data:
            parts.extend(
                [
                    f"Job: {profile_data['job_title'] or 'N/A'}",
                    f"Employment: {profile_data['employment_status'] or 'N/A'}",
                ]
            )

        parts.append(f"Income (Monthly approx): {total_income:.2f}")

        if goals_rows:
            goal_strs = [
                f"- {g['goal_name']} (Target: {float(g['target'] or 0):.2f})"
                for g in goals_rows
            ]
            parts.append("Active Goals: " + "; ".join(goal_strs))
        else:
            parts.append("Active Goals: None")

        if budgets_rows:
            budget_strs = [
                f"- {b['budget_name']} (ID: {b['id']}, Limit: {float(b['total_limit']):.2f})"
                for b in budgets_rows
            ]
            parts.append("Active Budgets: " + "; ".join(budget_strs))
        else:
            parts.append("Active Budgets: None")

        parts.append(f"Recent Spending (last 90d): {total_spent_90d:.2f}")

        if top_cats:
            cat_strs = [
                f"{c['type_spending']} ({float(c['total']):.2f})"
                for c in top_cats
                if c["type_spending"]
            ]
            if cat_strs:
                parts.append("Top Spending Categories: " + ", ".join(cat_strs))

        if top_stores:
            store_strs = [
                f"{s['store_name']} ({float(s['total']):.2f})"
                for s in top_stores
                if s["store_name"]
            ]
            if store_strs:
                parts.append("Top Stores: " + ", ".join(store_strs))

        return "\n".join(parts)

    except Exception as exc:
        logger.warning(f"Error building user summary for {user_id}: {exc}")
        return f"Error retrieving user summary for {user_id}."

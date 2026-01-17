import logging
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.models import Goal, Income, Profile, Transaction
from features.crud.budgets.service import fetch_active_budgets

logger = logging.getLogger(__name__)


# =============================================================================
# Data Fetching Functions
# =============================================================================


def fetch_user_profile(user_id: int) -> Optional[dict]:
    """
    Fetch basic user and profile information.

    Returns:
        dict with user and profile data, or None if user not found.
    """
    user_data = (
        User.objects.filter(id=user_id).values("first_name", "last_name").first()
    )

    if not user_data:
        return None

    profile_data = (
        Profile.objects.filter(user_id=user_id)
        .values("job_title", "employment_status")
        .first()
    )

    return {
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "job_title": profile_data.get("job_title") if profile_data else None,
        "employment_status": profile_data.get("employment_status")
        if profile_data
        else None,
    }


def fetch_income_total(user_id: int) -> Decimal:
    """
    Get total active income for the user.

    Returns:
        Total income as Decimal.
    """
    result = Income.objects.filter(user_id=user_id, active=True).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )
    return result["total"]


def fetch_active_goals(user_id: int) -> list[dict]:
    """
    Get active goals ordered by due date.

    Returns:
        List of goal dictionaries with goal_name, target, and due_date.
    """
    return list(
        Goal.objects.filter(user_id=user_id, active=True)
        .order_by("due_date")
        .values("id", "goal_name", "target", "due_date")
    )


def fetch_spending_stats(user_id: int, months_back: int = 3) -> dict:
    """
    Get spending statistics based on complete months.

    Calculates:
    - Average monthly spending from the last N COMPLETE months (excludes current month)
    - Current month spending so far
    - Top categories and stores from the historical period

    Args:
        user_id: The user's ID.
        months_back: Number of complete months to look back (default 3).

    Returns:
        dict containing monthly_average, current_month_spent, top_categories, top_stores.

    Example (if today is Jan 17, 2026):
        - Last 3 complete months: Oct, Nov, Dec 2025
        - monthly_average = (Oct + Nov + Dec) / 3
        - current_month_spent = Jan 1-17 spending
    """
    today = timezone.now().date()

    # Current month boundaries (for current month spending)
    current_month_start = today.replace(day=1)

    # Calculate start of historical period (N months before current month start)
    # Go back N months from the start of current month
    historical_start = current_month_start
    for _ in range(months_back):
        # Go to previous month
        historical_start = (historical_start - timedelta(days=1)).replace(day=1)

    # Historical period: from historical_start to end of last month (day before current month)
    historical_end = current_month_start - timedelta(days=1)

    # --- Current month spending ---
    current_month_result = Transaction.objects.filter(
        user_id=user_id,
        date__gte=current_month_start,
        date__lte=today,
        active=True,
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))
    current_month_spent = current_month_result["total"]

    # --- Historical spending (last N complete months) ---
    historical_result = Transaction.objects.filter(
        user_id=user_id,
        date__gte=historical_start,
        date__lte=historical_end,
        active=True,
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))
    historical_total = historical_result["total"]

    # Calculate monthly average (avoid division by zero)
    monthly_average = (
        historical_total / Decimal(months_back) if months_back > 0 else Decimal("0.00")
    )

    # --- Top categories (from historical period) ---
    top_categories = list(
        Transaction.objects.filter(
            user_id=user_id,
            date__gte=historical_start,
            date__lte=historical_end,
            active=True,
        )
        .values("type_spending")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    # --- Top stores (from historical period) ---
    top_stores = list(
        Transaction.objects.filter(
            user_id=user_id,
            date__gte=historical_start,
            date__lte=historical_end,
            active=True,
        )
        .values("store_name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:10]
    )

    return {
        "monthly_average": monthly_average,
        "current_month_spent": current_month_spent,
        "historical_total": historical_total,
        "months_back": months_back,
        "top_categories": top_categories,
        "top_stores": top_stores,
    }


# =============================================================================
# Formatting Functions
# =============================================================================


def format_profile_section(user_id: int, profile: dict) -> list[str]:
    """Format the profile section of the summary."""
    name = f"{profile['first_name']} {profile['last_name']}"
    parts = [
        f"Name: {name}",
        f"User ID: {user_id}",
    ]

    if profile.get("job_title") or profile.get("employment_status"):
        parts.append(f"Job: {profile.get('job_title') or 'N/A'}")
        parts.append(f"Employment: {profile.get('employment_status') or 'N/A'}")

    return parts


def format_income_section(income: Decimal) -> str:
    """Format the income section of the summary."""
    return f"Income (Monthly approx): {float(income):.2f}"


def format_goals_section(goals: list[dict]) -> str:
    """Format the goals section of the summary."""
    if not goals:
        return "Active Goals: None"

    goal_strs = [
        f"- {g['goal_name']} (ID: {g['id']}, Target: {float(g['target'] or 0):.2f}, Due: {g['due_date']})"
        for g in goals
    ]
    return "Active Goals: " + "; ".join(goal_strs)


def format_budgets_section(budgets: list[dict]) -> str:
    """Format the budgets section of the summary."""
    if not budgets:
        return "Active Budgets: None"

    budget_strs = [
        f"- {b['budget_name']} (ID: {b['id']}, Limit: {float(b['total_limit']):.2f})"
        for b in budgets
    ]
    return "Active Budgets: " + "; ".join(budget_strs)


def format_spending_section(spending_stats: dict) -> list[str]:
    """Format the spending section of the summary."""
    parts = []

    months_back = spending_stats.get("months_back", 3)
    monthly_average = spending_stats.get("monthly_average", Decimal("0.00"))
    current_month_spent = spending_stats.get("current_month_spent", Decimal("0.00"))

    parts.append(
        f"Avg Monthly Spending (last {months_back} months): {float(monthly_average):.2f}"
    )
    parts.append(f"Current Month Spending (so far): {float(current_month_spent):.2f}")

    # Top categories
    top_cats = spending_stats.get("top_categories", [])
    if top_cats:
        cat_strs = [
            f"{c['type_spending']} ({float(c['total']):.2f})"
            for c in top_cats
            if c.get("type_spending")
        ]
        if cat_strs:
            parts.append("Top Spending Categories: " + ", ".join(cat_strs))

    # Top stores
    top_stores = spending_stats.get("top_stores", [])
    if top_stores:
        store_strs = [
            f"{s['store_name']} ({float(s['total']):.2f})"
            for s in top_stores
            if s.get("store_name")
        ]
        if store_strs:
            parts.append("Top Stores: " + ", ".join(store_strs))

    return parts


def format_user_summary(
    user_id: int,
    profile: dict,
    income: Decimal,
    goals: list[dict],
    budgets: list[dict],
    spending_stats: dict,
) -> str:
    """
    Format all user data into a summary string.

    Args:
        user_id: The user's ID.
        profile: Profile data from fetch_user_profile.
        income: Total income from fetch_income_total.
        goals: Goals list from fetch_active_goals.
        budgets: Budgets list from fetch_active_budgets.
        spending_stats: Spending data from fetch_spending_stats.

    Returns:
        Formatted summary string.
    """
    parts = []

    # Profile section
    parts.extend(format_profile_section(user_id, profile))

    # Income section
    parts.append(format_income_section(income))

    # Goals section
    parts.append(format_goals_section(goals))

    # Budgets section
    parts.append(format_budgets_section(budgets))

    # Spending section
    parts.extend(format_spending_section(spending_stats))

    return "\n".join(parts)


# =============================================================================
# Main Orchestrator
# =============================================================================


def get_user_summary(user_id: int) -> str:
    """
    Fetch a brief user summary string tuned for goal-making/budgeting.

    Includes profile, income, active goals, active budgets, and recent spending.

    Args:
        user_id: The user's ID.

    Returns:
        A formatted summary string, or an error message if something fails.
    """
    try:
        # Fetch all data
        profile = fetch_user_profile(user_id)
        if not profile:
            return f"User {user_id} (no profile found)."

        income = fetch_income_total(user_id)
        goals = fetch_active_goals(user_id)
        budgets = fetch_active_budgets(user_id)
        spending_stats = fetch_spending_stats(user_id, months_back=3)

        # Format and return
        return format_user_summary(
            user_id=user_id,
            profile=profile,
            income=income,
            goals=goals,
            budgets=budgets,
            spending_stats=spending_stats,
        )

    except Exception as exc:
        logger.exception(f"Error building user summary for {user_id}")
        return f"Error retrieving user summary for {user_id}: {exc}"

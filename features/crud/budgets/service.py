from typing import List, Dict, Any
from core.models import Budget


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active budgets for a user."""
    budgets = (
        Budget.objects.filter(user_id=user_id, is_active=True)
        .order_by("-priority_level_int")
        .values("id", "budget_name", "total_limit", "priority_level_int")
    )
    return list(budgets)

"""Budgets database operations."""

import logging
from django.utils import timezone
from typing import Any, Dict, Optional

from ninja import Router, Query

from core.models import Budget
from core.utils.responses import success_response, error_response
from .schemas import BudgetCreateSchema, BudgetUpdateSchema

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# Fields for budget queries
BUDGET_FIELDS = (
    "id",
    "user_id",
    "budget_name",
    "description",
    "total_limit",
    "priority_level_int",
    "is_active",
    "active",
    "created_at",
    "updated_at",
)


def _format_budget(budget: Dict[str, Any]) -> Dict[str, Any]:
    """Format budget dict for JSON response."""
    budget["total_limit"] = (
        float(budget["total_limit"]) if budget["total_limit"] else 0.0
    )
    budget["active"] = budget.get("active", True)
    return budget


@router.get("/", response=Dict[str, Any])
def get_budgets(request, active: Optional[bool] = Query(None)):
    """Retrieve budgets for a user."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Budget.objects.filter(**filters)

    budgets = queryset.order_by("-priority_level_int").values(
        "id",
        "budget_name",
        "description",
        "total_limit",
        "priority_level_int",
        "is_active",
        "active",
        "created_at",
        "updated_at",
    )
    return success_response(list(budgets))


@router.get("/{budget_id}", response=Dict[str, Any])
def get_budget(request, budget_id: int):
    """Get a single budget."""
    budget = (
        Budget.objects.filter(id=budget_id, user_id=request.user.id)
        .values(
            "id",
            "user_id",
            "budget_name",
            "description",
            "total_limit",
            "priority_level_int",
            "is_active",
            "active",
            "created_at",
            "updated_at",
        )
        .first()
    )
    if not budget:
        return error_response("Budget not found", code=404)

    # Format total_limit
    budget["total_limit"] = (
        float(budget["total_limit"]) if budget["total_limit"] else 0.0
    )
    return success_response(budget)


@router.post("/", response=Dict[str, Any])
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    try:
        budget = Budget.objects.create(
            user_id=request.user.id,
            budget_name=payload.budget_name,
            description=payload.description,
            total_limit=payload.total_limit,
            priority_level_int=payload.priority_level_int,
            is_active=payload.is_active,
        )
        # Fetch created budget as dict
        created = Budget.objects.filter(id=budget.id).values(*BUDGET_FIELDS).first()
        return success_response(_format_budget(created), "Budget created successfully")
    except Exception as e:
        logger.exception("Failed to create budget")
        return error_response(f"Failed to create budget: {e}")


@router.put("/{budget_id}", response=Dict[str, Any])
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Budget.objects.filter(
            id=budget_id, user_id=request.user.id
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Budget not found", code=404)

        budget = Budget.objects.filter(id=budget_id).values(*BUDGET_FIELDS).first()
        return success_response(_format_budget(budget), "Budget updated successfully")
    except Exception as e:
        logger.exception("Failed to update budget")
        return error_response(f"Failed to update budget: {e}")


@router.delete("/{budget_id}", response=Dict[str, Any])
def delete_budget(request, budget_id: int):
    """Soft delete a budget by setting active to False."""
    try:
        rows_affected = Budget.objects.filter(
            id=budget_id, user_id=request.user.id
        ).update(active=False, updated_at=timezone.now())
        if rows_affected == 0:
            return error_response("Budget not found", code=404)

        return success_response(None, "Budget deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete budget")
        return error_response(f"Failed to delete budget: {e}")

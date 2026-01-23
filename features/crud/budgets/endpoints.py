"""Budgets database operations."""

import logging
from django.utils import timezone
from typing import Any, Dict, Optional

from ninja import Router, Query

from core.models import Budget
from core.utils.responses import success_response, error_response
from .schemas import (
    BudgetCreateSchema,
    BudgetUpdateSchema,
    BudgetResponse,
    BudgetListResponse,
)

from features.auth.api import AuthBearer
from django.db.models import Sum, Q, DecimalField, Count
from django.db.models.functions import Coalesce

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
    "active",
    "created_at",
    "updated_at",
)


def _compute_budget_stats(budget_obj, spent_amount, tx_count):
    """Compute derived fields for a budget object."""
    limit = float(budget_obj.total_limit)
    spent = float(spent_amount) if spent_amount else 0.0
    remaining = max(0, limit - spent)
    percentage_used = (spent / limit * 100) if limit > 0 else 0.0

    percentage_used = (spent / limit * 100) if limit > 0 else 0.0

    return {
        "id": budget_obj.id,
        "uuid": budget_obj.id,  # Keep id as standard, some frontends look for ids
        "budget_name": budget_obj.budget_name,
        "total_limit": limit,
        "priority_level": budget_obj.priority_level_int,  # legacy name support if needed? No, model has priority_level_int
        "priority_level_int": budget_obj.priority_level_int,
        "active": budget_obj.active,
        "created_at": budget_obj.created_at,
        "updated_at": budget_obj.updated_at,
        # Computed
        "spent": spent,
        "remaining": remaining,
        "percentage_used": round(percentage_used, 1),
        "transaction_count": tx_count,
        "description": budget_obj.description,
        "icon": budget_obj.icon,
        "color": budget_obj.color,
        "clean_description": budget_obj.description,  # Explicit alias for backward compatibility
    }


@router.get("/", response=BudgetListResponse)
def get_budgets(request, active: Optional[bool] = Query(None)):
    """Retrieve budgets for a user with computed stats."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    # Timeframe for "spent": Current Month
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    queryset = Budget.objects.filter(**filters)

    # Sorting
    if active is False:
        # Inactive/Deleted -> Sort by updated_at desc
        queryset = queryset.order_by("-updated_at")
    else:
        # Active -> Priority
        queryset = queryset.order_by("-priority_level_int")

    # Annotate spend and count
    # Note: Only count active EXPENSES
    budgets = queryset.annotate(
        monthly_spent=Coalesce(
            Sum(
                "transaction__amount",
                filter=Q(
                    transaction__date__gte=month_start,
                    transaction__active=True,
                    transaction__transaction_type="EXPENSE",
                ),
            ),
            0,
            output_field=DecimalField(),
        ),
        monthly_count=Count(
            "transaction__id",
            filter=Q(
                transaction__date__gte=month_start,
                transaction__active=True,
                transaction__transaction_type="EXPENSE",
            ),
        ),
    )

    result = []
    for b in budgets:
        result.append(_compute_budget_stats(b, b.monthly_spent, b.monthly_count))

    return success_response(result)


def _get_budget_with_stats(budget_id: int, user_id: int):
    """Helper to fetch a single budget with computed stats."""
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    budget = (
        Budget.objects.filter(id=budget_id, user_id=user_id)
        .annotate(
            monthly_spent=Coalesce(
                Sum(
                    "transaction__amount",
                    filter=Q(
                        transaction__date__gte=month_start,
                        transaction__active=True,
                        transaction__transaction_type="EXPENSE",
                    ),
                ),
                0,
                output_field=DecimalField(),
            ),
            monthly_count=Count(
                "transaction__id",
                filter=Q(
                    transaction__date__gte=month_start,
                    transaction__active=True,
                    transaction__transaction_type="EXPENSE",
                ),
            ),
        )
        .first()
    )

    if not budget:
        return None

    return _compute_budget_stats(budget, budget.monthly_spent, budget.monthly_count)


@router.get("/{budget_id}", response=BudgetResponse)
def get_budget(request, budget_id: int):
    """Get a single budget with computed stats."""
    result = _get_budget_with_stats(budget_id, request.user.id)
    if not result:
        return error_response("Budget not found", code=404)
    return success_response(result)


@router.post("/", response=BudgetResponse)
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    try:
        budget = Budget.objects.create(
            user_id=request.user.id,
            budget_name=payload.name,  # Map name -> budget_name
            description=payload.description,
            icon=payload.icon,
            color=payload.color,
            total_limit=payload.total_limit,
            priority_level_int=payload.priority_level_int,
        )
        # Fetch created budget with default stats (0 spent)
        result = _compute_budget_stats(budget, 0, 0)
        return success_response(result, "Budget created successfully")
    except Exception as e:
        logger.exception("Failed to create budget")
        return error_response(f"Failed to create budget: {e}")


@router.put("/{budget_id}", response=BudgetResponse)
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = timezone.now()

    # Map name -> budget_name
    if "name" in updates:
        updates["budget_name"] = updates.pop("name")

    try:
        rows_affected = Budget.objects.filter(
            id=budget_id, user_id=request.user.id
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Budget not found", code=404)

        result = _get_budget_with_stats(budget_id, request.user.id)
        return success_response(result, "Budget updated successfully")
    except Exception as e:
        logger.exception("Failed to update budget")
        return error_response(f"Failed to update budget: {e}")


@router.delete("/{budget_id}", response=BudgetResponse)
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

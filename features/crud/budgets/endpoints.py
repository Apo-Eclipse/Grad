"""Budgets database operations - CRUD only."""

import logging
from django.utils import timezone
from typing import Optional
from decimal import Decimal

from ninja import Router, Query
from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.models import Budget, Account
from core.utils.responses import success_response, error_response
from .schemas import (
    BudgetCreateSchema,
    BudgetUpdateSchema,
    BudgetResponse,
    BudgetListResponse,
)

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
    "icon",
    "color",
    "active",
    "created_at",
    "updated_at",
)


def _format_budget(budget: dict) -> dict:
    """Format budget dict for JSON response."""
    return {
        "id": budget["id"],
        "budget_name": budget["budget_name"],
        "description": budget.get("description"),
        "total_limit": float(budget["total_limit"]),
        "priority_level_int": budget.get("priority_level_int"),
        "icon": budget.get("icon"),
        "color": budget.get("color"),
        "active": budget.get("active", True),
        "created_at": budget["created_at"],
        "updated_at": budget.get("updated_at"),
    }


def _get_available_balance(user_id: int, exclude_budget_id: int = None) -> float:
    """Calculate available balance for budget allocation.

    Returns: total_regular_account_balance - sum_of_active_budget_limits
    Optionally excludes a specific budget (for updates).
    """
    # Sum of all active REGULAR account balances
    total_regular = Account.objects.filter(
        user_id=user_id, active=True, type=Account.AccountType.REGULAR
    ).aggregate(total=Coalesce(Sum("balance"), Decimal("0.00")))["total"]

    # Sum of all active budget limits (excluding the one being updated if applicable)
    budget_filter = {"user_id": user_id, "active": True}
    budget_queryset = Budget.objects.filter(**budget_filter)
    if exclude_budget_id:
        budget_queryset = budget_queryset.exclude(id=exclude_budget_id)

    total_allocated = budget_queryset.aggregate(
        total=Coalesce(Sum("total_limit"), Decimal("0.00"))
    )["total"]

    return float(total_regular) - float(total_allocated)


@router.get("/", response=BudgetListResponse)
def get_budgets(request, active: Optional[bool] = Query(None)):
    """Retrieve budgets for a user (raw data)."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Budget.objects.filter(**filters)

    # Sorting
    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-priority_level_int")

    budgets = queryset.values(*BUDGET_FIELDS)
    result = [_format_budget(b) for b in budgets]
    return success_response(result)


@router.get("/{budget_id}", response=BudgetResponse)
def get_budget(request, budget_id: int):
    """Get a single budget (raw data)."""
    budget = (
        Budget.objects.filter(id=budget_id, user_id=request.user.id)
        .values(*BUDGET_FIELDS)
        .first()
    )
    if not budget:
        return error_response("Budget not found", code=404)
    return success_response(_format_budget(budget))


@router.post("/", response=BudgetResponse)
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    try:
        # Check available balance
        available = _get_available_balance(request.user.id)
        if payload.total_limit > available:
            return error_response(
                f"Insufficient balance. Available: {available:.2f}, Requested: {payload.total_limit:.2f}",
                code=400,
            )

        budget = Budget.objects.create(
            user_id=request.user.id,
            budget_name=payload.name,
            description=payload.description,
            icon=payload.icon,
            color=payload.color,
            total_limit=payload.total_limit,
            priority_level_int=payload.priority_level_int,
        )

        # Construct response directly from instance to ensure immediate consistency
        data = {
            "id": budget.id,
            "budget_name": budget.budget_name,
            "description": budget.description,
            "total_limit": float(budget.total_limit),
            "priority_level_int": budget.priority_level_int,
            "icon": budget.icon,
            "color": budget.color,
            "active": budget.active,
            "created_at": budget.created_at,
            "updated_at": budget.updated_at,
        }

        return success_response(data, "Budget created successfully")
    except Exception as e:
        logger.exception("Failed to create budget")
        return error_response(f"Failed to create budget: {e}")


@router.put("/{budget_id}", response=BudgetResponse)
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # If total_limit is being updated, validate against available balance
    if "total_limit" in updates:
        current_budget = (
            Budget.objects.filter(id=budget_id, user_id=request.user.id)
            .values("total_limit")
            .first()
        )

        if not current_budget:
            return error_response("Budget not found", code=404)

        current_limit = float(current_budget["total_limit"])
        new_limit = float(updates["total_limit"])
        additional_needed = new_limit - current_limit

        if additional_needed > 0:
            available = _get_available_balance(
                request.user.id, exclude_budget_id=budget_id
            )
            if additional_needed > available:
                return error_response(
                    f"Insufficient balance. Available: {available:.2f}, Additional needed: {additional_needed:.2f}",
                    code=400,
                )

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

        budget = Budget.objects.filter(id=budget_id).values(*BUDGET_FIELDS).first()
        return success_response(_format_budget(budget), "Budget updated successfully")
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

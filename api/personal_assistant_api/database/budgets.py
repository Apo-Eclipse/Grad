"""Budgets database operations."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from ninja import Router, Query

from ..models import Budget
from ..core.responses import success_response, error_response
from .schemas import BudgetCreateSchema, BudgetUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


def _budget_to_dict(budget: Budget) -> Dict[str, Any]:
    """Convert Budget model instance to dictionary."""
    return {
        "id": budget.id,
        "user_id": budget.user_id,
        "budget_name": budget.budget_name,
        "description": budget.description,
        "total_limit": float(budget.total_limit) if budget.total_limit else 0.0,
        "priority_level_int": budget.priority_level_int,
        "is_active": budget.is_active,
        "created_at": budget.created_at,
        "updated_at": budget.updated_at,
    }


def fetch_active_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active budgets for a user (helper)."""
    budgets = (
        Budget.objects.filter(user_id=user_id, is_active=True)
        .order_by("-priority_level_int")
        .values("id", "budget_name", "total_limit", "priority_level_int")
    )
    return list(budgets)


@router.get("/", response=Dict[str, Any])
def get_budgets(request, user_id: int = Query(...)):
    """Retrieve active budgets for a user."""
    budgets = (
        Budget.objects.filter(user_id=user_id, is_active=True)
        .order_by("-priority_level_int")
        .values(
            "id",
            "budget_name",
            "description",
            "total_limit",
            "priority_level_int",
            "is_active",
            "created_at",
            "updated_at",
        )
    )
    return success_response(list(budgets))


@router.get("/{budget_id}", response=Dict[str, Any])
def get_budget(request, budget_id: int):
    """Get a single budget."""
    try:
        budget = Budget.objects.get(id=budget_id)
        return success_response(_budget_to_dict(budget))
    except Budget.DoesNotExist:
        return error_response("Budget not found", code=404)


@router.post("/", response=Dict[str, Any])
def create_budget(request, payload: BudgetCreateSchema):
    """Create a new budget."""
    try:
        budget = Budget.objects.create(
            user_id=payload.user_id,
            budget_name=payload.budget_name,
            description=payload.description,
            total_limit=payload.total_limit,
            priority_level_int=payload.priority_level_int,
            is_active=payload.is_active,
        )
        return success_response(_budget_to_dict(budget), "Budget created successfully")
    except Exception as e:
        logger.exception("Failed to create budget")
        return error_response(f"Failed to create budget: {e}")


@router.put("/{budget_id}", response=Dict[str, Any])
def update_budget(request, budget_id: int, payload: BudgetUpdateSchema):
    """Update an existing budget."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = datetime.now()

    try:
        rows_affected = Budget.objects.filter(id=budget_id).update(**updates)
        if rows_affected == 0:
            return error_response("Budget not found", code=404)

        budget = Budget.objects.get(id=budget_id)
        return success_response(_budget_to_dict(budget), "Budget updated successfully")
    except Budget.DoesNotExist:
        return error_response("Budget not found", code=404)
    except Exception as e:
        logger.exception("Failed to update budget")
        return error_response(f"Failed to update budget: {e}")


@router.delete("/{budget_id}", response=Dict[str, Any])
def delete_budget(request, budget_id: int):
    """Soft delete a budget."""
    try:
        rows_affected = Budget.objects.filter(id=budget_id).update(
            is_active=False, updated_at=datetime.now()
        )
        if rows_affected == 0:
            return error_response("Budget not found", code=404)

        return success_response(None, "Budget deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete budget")
        return error_response(f"Failed to delete budget: {e}")

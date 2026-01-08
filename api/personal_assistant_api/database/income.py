"""Income database operations."""

import logging
from datetime import datetime
from typing import Any, Dict

from ninja import Router, Query

from ..models import Income
from ..core.responses import success_response, error_response
from .schemas import IncomeCreateSchema, IncomeUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


def _income_to_dict(income: Income) -> Dict[str, Any]:
    """Convert Income model instance to dictionary."""
    return {
        "id": income.id,
        "user_id": income.user_id,
        "type_income": income.type_income,
        "amount": float(income.amount) if income.amount else None,
        "description": income.description,
        "created_at": income.created_at,
        "updated_at": income.updated_at,
    }


@router.get("/", response=Dict[str, Any])
def get_income(request, user_id: int = Query(...)):
    """Retrieve all income sources for a user."""
    incomes = (
        Income.objects.filter(user_id=user_id)
        .order_by("-created_at")
        .values(
            "id",
            "user_id",
            "type_income",
            "amount",
            "description",
            "created_at",
            "updated_at",
        )
    )
    return success_response(list(incomes))


@router.get("/{income_id}", response=Dict[str, Any])
def get_single_income(request, income_id: int):
    """Get a single income source."""
    try:
        income = Income.objects.get(id=income_id)
        return success_response(_income_to_dict(income))
    except Income.DoesNotExist:
        return error_response("Income not found", code=404)


@router.post("/", response=Dict[str, Any])
def create_income(request, payload: IncomeCreateSchema):
    """Add a new income source."""
    try:
        income = Income.objects.create(
            user_id=payload.user_id,
            type_income=payload.type_income,
            amount=payload.amount,
            description=payload.description,
        )
        return success_response(
            _income_to_dict(income), "Income source created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create income source")
        return error_response(f"Failed to create income source: {e}")


@router.put("/{income_id}", response=Dict[str, Any])
def update_income(request, income_id: int, payload: IncomeUpdateSchema):
    """Update an existing income source."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = datetime.now()

    try:
        rows_affected = Income.objects.filter(id=income_id).update(**updates)
        if rows_affected == 0:
            return error_response("Income not found", code=404)

        income = Income.objects.get(id=income_id)
        return success_response(_income_to_dict(income), "Income updated successfully")
    except Income.DoesNotExist:
        return error_response("Income not found", code=404)
    except Exception as e:
        logger.exception("Failed to update income")
        return error_response(f"Failed to update income: {e}")


@router.delete("/{income_id}", response=Dict[str, Any])
def delete_income(request, income_id: int):
    """Delete an income source permanently."""
    try:
        rows_affected, _ = Income.objects.filter(id=income_id).delete()
        if rows_affected == 0:
            return error_response("Income not found", code=404)

        return success_response(None, "Income deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete income")
        return error_response(f"Failed to delete income: {e}")

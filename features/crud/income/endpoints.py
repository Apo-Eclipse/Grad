"""Income database operations."""

import logging
from django.utils import timezone
from typing import Any, Dict

from ninja import Router, Query

from core.models import Income
from core.utils.responses import success_response, error_response
from core.schemas.database import IncomeCreateSchema, IncomeUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


# Fields for income queries
INCOME_FIELDS = (
    "id",
    "user_id",
    "type_income",
    "amount",
    "description",
    "created_at",
    "updated_at",
)


def _format_income(income: Dict[str, Any]) -> Dict[str, Any]:
    """Format income dict for JSON response."""
    income["amount"] = float(income["amount"]) if income["amount"] else None
    return income


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
    income = (
        Income.objects.filter(id=income_id)
        .values(
            "id",
            "user_id",
            "type_income",
            "amount",
            "description",
            "created_at",
            "updated_at",
        )
        .first()
    )
    if not income:
        return error_response("Income not found", code=404)

    # Format amount
    income["amount"] = float(income["amount"]) if income["amount"] else None
    return success_response(income)


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
        # Fetch created income as dict
        created = Income.objects.filter(id=income.id).values(*INCOME_FIELDS).first()
        return success_response(
            _format_income(created), "Income source created successfully"
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

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Income.objects.filter(id=income_id).update(**updates)
        if rows_affected == 0:
            return error_response("Income not found", code=404)

        income = Income.objects.filter(id=income_id).values(*INCOME_FIELDS).first()
        return success_response(_format_income(income), "Income updated successfully")
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

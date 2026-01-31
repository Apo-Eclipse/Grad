"""Income database operations."""

import logging
import calendar
from decimal import Decimal
from django.utils import timezone
from typing import Any, Dict, Optional
from asgiref.sync import sync_to_async

from ninja import Router, Query

from core.models import Income, Account
from core.utils.responses import success_response, error_response
from .schemas import (
    IncomeCreateSchema,
    IncomeUpdateSchema,
    IncomeResponse,
    IncomeListResponse,
)
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# Fields for income queries
INCOME_FIELDS = (
    "id",
    "user_id",
    "account_id",
    "type_income",
    "amount",
    "description",
    "active",
    "created_at",
    "updated_at",
    "payment_day",
    "next_payment_date",
)


def _format_income(income: Dict[str, Any]) -> Dict[str, Any]:
    """Format income dict for JSON response."""
    income["amount"] = float(income["amount"]) if income["amount"] else None
    income["active"] = income.get("active", True)
    income["payment_day"] = income.get("payment_day")
    income["next_payment_date"] = income.get("next_payment_date")

    # Static visual fields
    income["icon"] = "cash-outline"
    income["color"] = "#10b981"

    return income


@router.get("/", response=IncomeListResponse)
async def get_income(request, active: Optional[bool] = Query(None)):
    """Retrieve all income sources for a user."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Income.objects.filter(**filters)
    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-amount")

    incomes = [i async for i in queryset.values(*INCOME_FIELDS)]
    result = [_format_income(i) for i in incomes]
    return success_response(result)


@router.get("/{income_id}", response=IncomeResponse)
async def get_single_income(request, income_id: int):
    """Get a single income source."""
    income = await (
        Income.objects.filter(id=income_id, user_id=request.user.id)
        .values(*INCOME_FIELDS)
        .afirst()
    )
    if not income:
        return error_response("Income not found", code=404)
    return success_response(_format_income(income))


@router.post("/", response=IncomeResponse)
async def create_income(request, payload: IncomeCreateSchema):
    """Add a new income source."""
    try:
        # Validate account if provided - complex logic kept in sync_to_async
        @sync_to_async
        def create_income_record():
            # Validate account if provided
            account = None
            if payload.account_id:
                try:
                    account = Account.objects.get(
                        id=payload.account_id, user_id=request.user.id, active=True
                    )
                except Account.DoesNotExist:
                    return None, "Account not found or does not belong to user"

            income = Income.objects.create(
                user_id=request.user.id,
                account=account,
                type_income=payload.type_income,
                amount=payload.amount,
                description=payload.description,
                payment_day=payload.payment_day,
            )

            # Handle Recurring vs One-time Logic
            should_pay_now = False
            if payload.payment_day:
                today = timezone.now().date()
                should_pay_now = payload.payment_day == today.day

                def get_safe_date(year, month, day):
                    while month > 12:
                        month -= 12
                        year += 1
                    _, last = calendar.monthrange(year, month)
                    return today.replace(year=year, month=month, day=min(day, last))

                if should_pay_now:
                    income.next_payment_date = get_safe_date(
                        today.year, today.month + 1, payload.payment_day
                    )
                elif payload.payment_day > today.day:
                    income.next_payment_date = get_safe_date(
                        today.year, today.month, payload.payment_day
                    )
                else:
                    income.next_payment_date = get_safe_date(
                        today.year, today.month + 1, payload.payment_day
                    )

                income.save()
            else:
                should_pay_now = True

            # Update account balance if needed
            if should_pay_now and account:
                account.balance += Decimal(str(payload.amount))
                account.save(update_fields=["balance"])

            created = Income.objects.filter(id=income.id).values(*INCOME_FIELDS).first()
            return created, None

        result, error = await create_income_record()
        if error:
            return error_response(error, code=404)
        return success_response(
            _format_income(result), "Income source created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create income source")
        return error_response(f"Failed to create income source: {e}")


@router.put("/{income_id}", response=IncomeResponse)
async def update_income(request, income_id: int, payload: IncomeUpdateSchema):
    """Update an existing income source."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = timezone.now()

    # Recalculate next_payment_date if payment_day is changing
    if "payment_day" in updates and updates["payment_day"] is not None:
        p_day = updates["payment_day"]
        today = timezone.now().date()

        target_month = today.month
        target_year = today.year

        if p_day <= today.day:
            target_month += 1

        if target_month > 12:
            target_month = 1
            target_year += 1

        _, last_day = calendar.monthrange(target_year, target_month)
        target_day = min(p_day, last_day)

        updates["next_payment_date"] = today.replace(
            year=target_year, month=target_month, day=target_day
        )

    try:
        rows_affected = await Income.objects.filter(
            id=income_id, user_id=request.user.id
        ).aupdate(**updates)
        if rows_affected == 0:
            return error_response("Income not found", code=404)
        income = (
            await Income.objects.filter(id=income_id).values(*INCOME_FIELDS).afirst()
        )
        return success_response(_format_income(income), "Income updated successfully")
    except Exception as e:
        logger.exception("Failed to update income")
        return error_response(f"Failed to update income: {e}")


@router.delete("/{income_id}", response=IncomeResponse)
async def delete_income(request, income_id: int):
    """Soft delete an income source by setting active to False."""
    try:
        rows_affected = await Income.objects.filter(
            id=income_id, user_id=request.user.id
        ).aupdate(active=False, updated_at=timezone.now())
        if rows_affected == 0:
            return error_response("Income not found", code=404)
        return success_response(None, "Income deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete income")
        return error_response(f"Failed to delete income: {e}")

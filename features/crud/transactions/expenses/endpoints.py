"""Expense transactions - CRUD operations."""

import logging
from decimal import Decimal
from typing import Optional

from ninja import Router, Query
from django.utils import timezone

from core.models import Transaction, Account
from core.utils.responses import success_response, error_response
from ..utils import TRANSACTION_FIELDS, format_transaction
from ..schemas import TransactionResponse, TransactionListResponse
from .schemas import ExpenseCreateSchema, ExpenseUpdateSchema
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/", response=TransactionListResponse)
def get_expenses(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve expense transactions for a user."""
    filters = {"user_id": request.user.id, "transaction_type": "EXPENSE"}
    if active is not None:
        filters["active"] = active
    if start_date:
        filters["date__gte"] = start_date
    if end_date:
        filters["date__lte"] = end_date

    queryset = Transaction.objects.filter(**filters)

    if active is False:
        ordering = ("-updated_at",)
    else:
        ordering = ("-date", "-created_at")

    transactions = queryset.order_by(*ordering).values(*TRANSACTION_FIELDS)[:limit]
    result = [format_transaction(txn) for txn in transactions]
    return success_response(result)


@router.get("/{expense_id}", response=TransactionResponse)
def get_expense(request, expense_id: int):
    """Get a single expense transaction."""
    txn = (
        Transaction.objects.filter(
            id=expense_id, user_id=request.user.id, transaction_type="EXPENSE"
        )
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Expense not found", code=404)
    return success_response(format_transaction(txn))


@router.post("/", response=TransactionResponse)
def create_expense(request, payload: ExpenseCreateSchema):
    """Create a new expense transaction. Deducts from account balance."""
    try:
        account = None
        if payload.account_id:
            try:
                account = Account.objects.get(
                    id=payload.account_id, user_id=request.user.id, active=True
                )
            except Account.DoesNotExist:
                return error_response(
                    "Account not found or does not belong to user", code=404
                )

            if account.balance < payload.amount:
                return error_response(
                    f"Insufficient balance. Available: {float(account.balance):.2f}, Required: {payload.amount:.2f}",
                    code=400,
                )

        txn = Transaction.objects.create(
            user_id=request.user.id,
            date=payload.date,
            amount=payload.amount,
            description=payload.description,
            city=payload.city,
            budget_id=payload.budget_id,
            neighbourhood=payload.neighbourhood,
            account_id=payload.account_id,
            transaction_type="EXPENSE",
        )

        # Deduct from account balance
        if account:
            account.balance -= Decimal(str(payload.amount))
            account.save(update_fields=["balance"])

        created = (
            Transaction.objects.filter(id=txn.id).values(*TRANSACTION_FIELDS).first()
        )
        return success_response(
            format_transaction(created), "Expense created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create expense")
        return error_response(f"Failed to create expense: {e}")


@router.put("/{expense_id}", response=TransactionResponse)
def update_expense(request, expense_id: int, payload: ExpenseUpdateSchema):
    """Update an existing expense. Adjusts account balance if amount changes."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    current_txn = Transaction.objects.filter(
        id=expense_id, user_id=request.user.id, transaction_type="EXPENSE"
    ).first()

    if not current_txn:
        return error_response("Expense not found", code=404)

    # Handle balance adjustment if amount is changing
    if "amount" in updates and current_txn.account_id:
        old_amount = float(current_txn.amount)
        new_amount = float(updates["amount"])
        difference = new_amount - old_amount

        if difference > 0:  # Increasing expense
            account = Account.objects.get(id=current_txn.account_id)
            if account.balance < difference:
                return error_response(
                    f"Insufficient balance. Available: {float(account.balance):.2f}, Additional needed: {difference:.2f}",
                    code=400,
                )
            account.balance -= Decimal(str(difference))
            account.save(update_fields=["balance"])
        elif difference < 0:  # Decreasing expense
            account = Account.objects.get(id=current_txn.account_id)
            account.balance += Decimal(str(abs(difference)))
            account.save(update_fields=["balance"])

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Transaction.objects.filter(
            id=expense_id, user_id=request.user.id, transaction_type="EXPENSE"
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Expense not found", code=404)

        txn = (
            Transaction.objects.filter(id=expense_id)
            .values(*TRANSACTION_FIELDS)
            .first()
        )
        return success_response(format_transaction(txn), "Expense updated successfully")
    except Exception as e:
        logger.exception("Failed to update expense")
        return error_response(f"Failed to update expense: {e}")


@router.delete("/{expense_id}", response=TransactionResponse)
def delete_expense(request, expense_id: int):
    """Soft delete an expense. Refunds account balance."""
    try:
        txn = Transaction.objects.filter(
            id=expense_id,
            user_id=request.user.id,
            transaction_type="EXPENSE",
            active=True,
        ).first()

        if not txn:
            return error_response("Expense not found", code=404)

        # Refund balance
        if txn.account_id:
            account = Account.objects.get(id=txn.account_id)
            account.balance += txn.amount
            account.save(update_fields=["balance"])

        txn.active = False
        txn.updated_at = timezone.now()
        txn.save(update_fields=["active", "updated_at"])

        return success_response(None, "Expense deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete expense")
        return error_response(f"Failed to delete expense: {e}")

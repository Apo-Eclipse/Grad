"""Transactions database operations - CRUD only."""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from ninja import Router, Query
from django.utils import timezone

from core.models import Transaction, Account
from core.utils.responses import success_response, error_response

from .schemas import (
    TransactionCreateSchema,
    TransactionUpdateSchema,
    TransactionResponse,
    TransactionListResponse,
)

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# Fields to retrieve for transaction queries
TRANSACTION_FIELDS = (
    "id",
    "user_id",
    "date",
    "amount",
    "time",
    "description",
    "city",
    "budget_id",
    "neighbourhood",
    "active",
    "created_at",
    "updated_at",
    "transaction_type",
    "account_id",
    "transfer_to_id",
)


def _format_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Format transaction dict for JSON response."""
    return {
        "id": txn["id"],
        "user_id": txn["user_id"],
        "date": txn["date"],
        "amount": float(txn["amount"]) if txn["amount"] else 0.0,
        "time": str(txn["time"]) if txn["time"] else None,
        "description": txn.get("description"),
        "city": txn.get("city"),
        "budget_id": txn.get("budget_id"),
        "neighbourhood": txn.get("neighbourhood"),
        "account_id": txn.get("account_id"),
        "transfer_to_id": txn.get("transfer_to_id"),
        "transaction_type": txn.get("transaction_type", "EXPENSE"),
        "active": txn.get("active", True),
        "created_at": txn["created_at"],
        "updated_at": txn.get("updated_at"),
    }


@router.get("/", response=TransactionListResponse)
def get_transactions(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve transactions for a user (raw data)."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active
    if start_date:
        filters["date__gte"] = start_date
    if end_date:
        filters["date__lte"] = end_date
    if transaction_type:
        filters["transaction_type"] = transaction_type

    queryset = Transaction.objects.filter(**filters)

    if active is False:
        ordering = ("-updated_at",)
    else:
        ordering = ("-date", "-time")

    transactions = queryset.order_by(*ordering).values(*TRANSACTION_FIELDS)[:limit]
    result = [_format_transaction(txn) for txn in transactions]
    return success_response(result)


@router.get("/{transaction_id}", response=TransactionResponse)
def get_transaction(request, transaction_id: int):
    """Get a single transaction (raw data)."""
    txn = (
        Transaction.objects.filter(id=transaction_id, user_id=request.user.id)
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Transaction not found", code=404)
    return success_response(_format_transaction(txn))


@router.post("/", response=TransactionResponse)
def create_transaction(request, payload: TransactionCreateSchema):
    """Create a new transaction row."""
    try:
        # Validate and deduct from account for EXPENSE transactions
        account = None
        if payload.account_id and payload.transaction_type == "EXPENSE":
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
            time=payload.time,
            description=payload.description,
            city=payload.city,
            budget_id=payload.budget_id,
            neighbourhood=payload.neighbourhood,
            account_id=payload.account_id,
            transaction_type=payload.transaction_type,
        )

        # Deduct from account balance for expenses
        if account:
            account.balance -= Decimal(str(payload.amount))
            account.save(update_fields=["balance"])

        created = (
            Transaction.objects.filter(id=txn.id).values(*TRANSACTION_FIELDS).first()
        )
        return success_response(
            _format_transaction(created), "Transaction created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create transaction")
        return error_response(f"Failed to create transaction: {e}")


@router.put("/{transaction_id}", response=TransactionResponse)
def update_transaction(request, transaction_id: int, payload: TransactionUpdateSchema):
    """Update an existing transaction."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # Get current transaction to check amount changes
    current_txn = Transaction.objects.filter(
        id=transaction_id, user_id=request.user.id
    ).first()

    if not current_txn:
        return error_response("Transaction not found", code=404)

    # Handle balance adjustment if amount is changing for EXPENSE with account
    if (
        "amount" in updates
        and current_txn.transaction_type == "EXPENSE"
        and current_txn.account_id
    ):
        old_amount = float(current_txn.amount)
        new_amount = float(updates["amount"])
        difference = new_amount - old_amount

        if difference > 0:  # Increasing expense, need to deduct more
            account = Account.objects.get(id=current_txn.account_id)
            if account.balance < difference:
                return error_response(
                    f"Insufficient balance. Available: {float(account.balance):.2f}, Additional needed: {difference:.2f}",
                    code=400,
                )
            account.balance -= Decimal(str(difference))
            account.save(update_fields=["balance"])
        elif difference < 0:  # Decreasing expense, refund the difference
            account = Account.objects.get(id=current_txn.account_id)
            account.balance += Decimal(str(abs(difference)))
            account.save(update_fields=["balance"])

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Transaction.objects.filter(
            id=transaction_id, user_id=request.user.id
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Transaction not found", code=404)

        txn = (
            Transaction.objects.filter(id=transaction_id)
            .values(*TRANSACTION_FIELDS)
            .first()
        )
        return success_response(
            _format_transaction(txn), "Transaction updated successfully"
        )
    except Exception as e:
        logger.exception("Failed to update transaction")
        return error_response(f"Failed to update transaction: {e}")


@router.delete("/{transaction_id}", response=TransactionResponse)
def delete_transaction(request, transaction_id: int):
    """Soft delete a transaction by setting active to False."""
    try:
        # Get transaction to refund balance if it's an expense with account
        txn = Transaction.objects.filter(
            id=transaction_id, user_id=request.user.id, active=True
        ).first()

        if not txn:
            return error_response("Transaction not found", code=404)

        # Refund balance for EXPENSE transactions with account
        if txn.transaction_type == "EXPENSE" and txn.account_id:
            account = Account.objects.get(id=txn.account_id)
            account.balance += txn.amount
            account.save(update_fields=["balance"])

        txn.active = False
        txn.updated_at = timezone.now()
        txn.save(update_fields=["active", "updated_at"])

        return success_response(None, "Transaction deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete transaction")
        return error_response(f"Failed to delete transaction: {e}")

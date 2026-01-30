"""Deposit transactions - CRUD operations."""

import logging
from decimal import Decimal
from typing import Optional

from ninja import Router, Query
from django.utils import timezone

from core.models import Transaction, Account
from core.utils.responses import success_response, error_response
from ..utils import TRANSACTION_FIELDS, format_transaction
from ..schemas import TransactionResponse, TransactionListResponse
from .schemas import DepositCreateSchema, DepositUpdateSchema
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/", response=TransactionListResponse)
def get_deposits(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve deposit transactions for a user."""
    filters = {"user_id": request.user.id, "transaction_type": "DEPOSIT"}
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


@router.get("/{deposit_id}", response=TransactionResponse)
def get_deposit(request, deposit_id: int):
    """Get a single deposit transaction."""
    txn = (
        Transaction.objects.filter(
            id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
        )
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Deposit not found", code=404)
    return success_response(format_transaction(txn))


@router.post("/", response=TransactionResponse)
def create_deposit(request, payload: DepositCreateSchema):
    """Create a new deposit transaction. Adds to account balance."""
    try:
        if payload.amount <= 0:
            return error_response("Amount must be positive", code=400)

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

        txn = Transaction.objects.create(
            user_id=request.user.id,
            date=payload.date,
            amount=payload.amount,
            description=payload.description,
            account_id=payload.account_id,
            transaction_type="DEPOSIT",
        )

        # Add to account balance
        if account:
            account.balance += Decimal(str(payload.amount))
            account.save(update_fields=["balance"])

        created = (
            Transaction.objects.filter(id=txn.id).values(*TRANSACTION_FIELDS).first()
        )
        return success_response(
            format_transaction(created), "Deposit created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create deposit")
        return error_response(f"Failed to create deposit: {e}")


@router.put("/{deposit_id}", response=TransactionResponse)
def update_deposit(request, deposit_id: int, payload: DepositUpdateSchema):
    """Update an existing deposit. Adjusts account balance if amount changes."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    current_txn = Transaction.objects.filter(
        id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
    ).first()

    if not current_txn:
        return error_response("Deposit not found", code=404)

    # Handle balance adjustment if amount is changing
    if "amount" in updates and current_txn.account_id:
        old_amount = float(current_txn.amount)
        new_amount = float(updates["amount"])
        difference = new_amount - old_amount

        account = Account.objects.get(id=current_txn.account_id)
        if difference > 0:  # Increasing deposit
            account.balance += Decimal(str(difference))
        elif difference < 0:  # Decreasing deposit
            # Check if we can decrease (don't go negative)
            if account.balance < abs(difference):
                return error_response(
                    f"Cannot reduce deposit. Would make balance negative. Available: {float(account.balance):.2f}",
                    code=400,
                )
            account.balance -= Decimal(str(abs(difference)))
        account.save(update_fields=["balance"])

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Transaction.objects.filter(
            id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Deposit not found", code=404)

        txn = (
            Transaction.objects.filter(id=deposit_id)
            .values(*TRANSACTION_FIELDS)
            .first()
        )
        return success_response(format_transaction(txn), "Deposit updated successfully")
    except Exception as e:
        logger.exception("Failed to update deposit")
        return error_response(f"Failed to update deposit: {e}")


@router.delete("/{deposit_id}", response=TransactionResponse)
def delete_deposit(request, deposit_id: int):
    """Soft delete a deposit. Deducts from account balance."""
    try:
        txn = Transaction.objects.filter(
            id=deposit_id,
            user_id=request.user.id,
            transaction_type="DEPOSIT",
            active=True,
        ).first()

        if not txn:
            return error_response("Deposit not found", code=404)

        # Deduct from balance (reverse the deposit)
        if txn.account_id:
            account = Account.objects.get(id=txn.account_id)
            if account.balance < txn.amount:
                return error_response(
                    f"Cannot delete deposit. Would make balance negative. Available: {float(account.balance):.2f}",
                    code=400,
                )
            account.balance -= txn.amount
            account.save(update_fields=["balance"])

        txn.active = False
        txn.updated_at = timezone.now()
        txn.save(update_fields=["active", "updated_at"])

        return success_response(None, "Deposit deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete deposit")
        return error_response(f"Failed to delete deposit: {e}")

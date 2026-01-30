"""Transfer transactions - CRUD operations."""

import logging
from typing import Optional

from ninja import Router, Query
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import F

from core.models import Transaction, Account
from core.utils.responses import success_response, error_response
from ..utils import TRANSACTION_FIELDS, format_transaction
from ..schemas import TransactionResponse, TransactionListResponse
from .schemas import TransferCreateSchema
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/", response=TransactionListResponse)
def get_transfers(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve transfer transactions for a user."""
    filters = {"user_id": request.user.id, "transaction_type": "TRANSFER"}
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


@router.get("/{transfer_id}", response=TransactionResponse)
def get_transfer(request, transfer_id: int):
    """Get a single transfer transaction."""
    txn = (
        Transaction.objects.filter(
            id=transfer_id, user_id=request.user.id, transaction_type="TRANSFER"
        )
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Transfer not found", code=404)
    return success_response(format_transaction(txn))


@router.post("/", response=TransactionResponse)
def create_transfer(request, payload: TransferCreateSchema):
    """Create a transfer between accounts."""
    if payload.amount <= 0:
        return error_response("Amount must be positive", code=400)

    with db_transaction.atomic():
        try:
            from_acc = Account.objects.select_for_update().get(
                id=payload.from_account_id, user=request.user, active=True
            )
            to_acc = Account.objects.select_for_update().get(
                id=payload.to_account_id, user=request.user, active=True
            )
        except Account.DoesNotExist:
            return error_response("One or both accounts not found", code=404)

        if from_acc.id == to_acc.id:
            return error_response("Cannot transfer to the same account", code=400)

        # Check balance for source account
        if from_acc.balance < payload.amount:
            return error_response(
                f"Insufficient balance. Available: {float(from_acc.balance):.2f}, Required: {payload.amount:.2f}",
                code=400,
            )

        # Update balances
        from_acc.balance = F("balance") - payload.amount
        to_acc.balance = F("balance") + payload.amount
        from_acc.save(update_fields=["balance"])
        to_acc.save(update_fields=["balance"])

        from_acc.refresh_from_db()
        to_acc.refresh_from_db()

        # Create transaction record
        txn = Transaction.objects.create(
            user=request.user,
            transaction_type="TRANSFER",
            date=payload.date or timezone.now().date(),
            amount=payload.amount,
            description=payload.description
            or f"Transfer from {from_acc.name} to {to_acc.name}",
            account=from_acc,
            transfer_to=to_acc,
        )

        created = (
            Transaction.objects.filter(id=txn.id).values(*TRANSACTION_FIELDS).first()
        )
        return success_response(
            format_transaction(created), "Transfer completed successfully"
        )


@router.delete("/{transfer_id}", response=TransactionResponse)
def delete_transfer(request, transfer_id: int):
    """Soft delete/reverse a transfer. Moves funds back."""
    try:
        txn = Transaction.objects.filter(
            id=transfer_id,
            user_id=request.user.id,
            transaction_type="TRANSFER",
            active=True,
        ).first()

        if not txn:
            return error_response("Transfer not found", code=404)

        # Reverse the transfer
        with db_transaction.atomic():
            if txn.account_id and txn.transfer_to_id:
                from_acc = Account.objects.select_for_update().get(id=txn.account_id)
                to_acc = Account.objects.select_for_update().get(id=txn.transfer_to_id)

                # Move funds back
                from_acc.balance = F("balance") + txn.amount
                to_acc.balance = F("balance") - txn.amount
                from_acc.save(update_fields=["balance"])
                to_acc.save(update_fields=["balance"])

            txn.active = False
            txn.updated_at = timezone.now()
            txn.save(update_fields=["active", "updated_at"])

        return success_response(None, "Transfer reversed and deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete transfer")
        return error_response(f"Failed to delete transfer: {e}")

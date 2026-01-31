"""Deposit transactions - CRUD operations."""

import logging
from decimal import Decimal
from typing import Optional
from asgiref.sync import sync_to_async

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
async def get_deposits(
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

    # Use async for with limit
    transactions = []
    count = 0
    async for txn in queryset.order_by(*ordering).values(*TRANSACTION_FIELDS):
        if count >= limit:
            break
        transactions.append(txn)
        count += 1

    result = [format_transaction(txn) for txn in transactions]
    return success_response(result)


@router.get("/{deposit_id}", response=TransactionResponse)
async def get_deposit(request, deposit_id: int):
    """Get a single deposit transaction."""
    txn = await (
        Transaction.objects.filter(
            id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
        )
        .values(*TRANSACTION_FIELDS)
        .afirst()
    )
    if not txn:
        return error_response("Deposit not found", code=404)
    return success_response(format_transaction(txn))


@router.post("/", response=TransactionResponse)
async def create_deposit(request, payload: DepositCreateSchema):
    """Create a new deposit transaction. Adds to account balance."""
    if payload.amount <= 0:
        return error_response("Amount must be positive", code=400)

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def create_deposit_record():
        try:
            account = None
            if payload.account_id:
                try:
                    account = Account.objects.get(
                        id=payload.account_id, user_id=request.user.id, active=True
                    )
                except Account.DoesNotExist:
                    return None, "Account not found or does not belong to user"

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
                Transaction.objects.filter(id=txn.id)
                .values(*TRANSACTION_FIELDS)
                .first()
            )
            return created, None
        except Exception as e:
            logger.exception("Failed to create deposit")
            return None, str(e)

    result, error = await create_deposit_record()
    if error:
        return error_response(
            error if "not found" in error else f"Failed to create deposit: {error}",
            code=400,
        )
    return success_response(format_transaction(result), "Deposit created successfully")


@router.put("/{deposit_id}", response=TransactionResponse)
async def update_deposit(request, deposit_id: int, payload: DepositUpdateSchema):
    """Update an existing deposit. Adjusts account balance if amount changes."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def update_deposit_record():
        current_txn = Transaction.objects.filter(
            id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
        ).first()

        if not current_txn:
            return None, "Deposit not found"

        # Handle balance adjustment if amount is changing
        if "amount" in updates and current_txn.account_id:
            old_amount = float(current_txn.amount)
            new_amount = float(updates["amount"])
            difference = new_amount - old_amount

            account = Account.objects.get(id=current_txn.account_id)
            if difference > 0:  # Increasing deposit
                account.balance += Decimal(str(difference))
            elif difference < 0:  # Decreasing deposit
                if account.balance < abs(difference):
                    return (
                        None,
                        f"Cannot reduce deposit. Would make balance negative. Available: {float(account.balance):.2f}",
                    )
                account.balance -= Decimal(str(abs(difference)))
            account.save(update_fields=["balance"])

        updates["updated_at"] = timezone.now()

        try:
            rows_affected = Transaction.objects.filter(
                id=deposit_id, user_id=request.user.id, transaction_type="DEPOSIT"
            ).update(**updates)
            if rows_affected == 0:
                return None, "Deposit not found"

            txn = (
                Transaction.objects.filter(id=deposit_id)
                .values(*TRANSACTION_FIELDS)
                .first()
            )
            return txn, None
        except Exception as e:
            logger.exception("Failed to update deposit")
            return None, str(e)

    result, error = await update_deposit_record()
    if error:
        return error_response(error, code=404 if "not found" in error else 400)
    return success_response(format_transaction(result), "Deposit updated successfully")


@router.delete("/{deposit_id}", response=TransactionResponse)
async def delete_deposit(request, deposit_id: int):
    """Soft delete a deposit. Deducts from account balance."""

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def soft_delete_deposit():
        try:
            txn = Transaction.objects.filter(
                id=deposit_id,
                user_id=request.user.id,
                transaction_type="DEPOSIT",
                active=True,
            ).first()

            if not txn:
                return False, "Deposit not found"

            # Deduct from balance (reverse the deposit)
            if txn.account_id:
                account = Account.objects.get(id=txn.account_id)
                if account.balance < txn.amount:
                    return (
                        False,
                        f"Cannot delete deposit. Would make balance negative. Available: {float(account.balance):.2f}",
                    )
                account.balance -= txn.amount
                account.save(update_fields=["balance"])

            txn.active = False
            txn.updated_at = timezone.now()
            txn.save(update_fields=["active", "updated_at"])

            return True, None
        except Exception as e:
            logger.exception("Failed to delete deposit")
            return False, str(e)

    success, error = await soft_delete_deposit()
    if not success:
        return error_response(error, code=404 if "not found" in error else 400)
    return success_response(None, "Deposit deleted successfully")

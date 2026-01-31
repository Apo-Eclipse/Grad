"""Expense transactions - CRUD operations."""

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
from .schemas import ExpenseCreateSchema, ExpenseUpdateSchema
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/", response=TransactionListResponse)
async def get_expenses(
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


@router.get("/{expense_id}", response=TransactionResponse)
async def get_expense(request, expense_id: int):
    """Get a single expense transaction."""
    txn = await (
        Transaction.objects.filter(
            id=expense_id, user_id=request.user.id, transaction_type="EXPENSE"
        )
        .values(*TRANSACTION_FIELDS)
        .afirst()
    )
    if not txn:
        return error_response("Expense not found", code=404)
    return success_response(format_transaction(txn))


@router.post("/", response=TransactionResponse)
async def create_expense(request, payload: ExpenseCreateSchema):
    """Create a new expense transaction. Deducts from account balance."""

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def create_expense_record():
        try:
            account = None
            if payload.account_id:
                try:
                    account = Account.objects.get(
                        id=payload.account_id, user_id=request.user.id, active=True
                    )
                except Account.DoesNotExist:
                    return None, "Account not found or does not belong to user"

                if account.balance < payload.amount:
                    return (
                        None,
                        f"Insufficient balance. Available: {float(account.balance):.2f}, Required: {payload.amount:.2f}",
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
                Transaction.objects.filter(id=txn.id)
                .values(*TRANSACTION_FIELDS)
                .first()
            )
            return created, None
        except Exception as e:
            logger.exception("Failed to create expense")
            return None, str(e)

    result, error = await create_expense_record()
    if error:
        return error_response(
            error
            if "Insufficient" in error or "not found" in error
            else f"Failed to create expense: {error}",
            code=400,
        )
    return success_response(format_transaction(result), "Expense created successfully")


@router.put("/{expense_id}", response=TransactionResponse)
async def update_expense(request, expense_id: int, payload: ExpenseUpdateSchema):
    """Update an existing expense. Adjusts account balance if amount changes."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def update_expense_record():
        current_txn = Transaction.objects.filter(
            id=expense_id, user_id=request.user.id, transaction_type="EXPENSE"
        ).first()

        if not current_txn:
            return None, "Expense not found"

        # Handle balance adjustment if amount is changing
        if "amount" in updates and current_txn.account_id:
            old_amount = float(current_txn.amount)
            new_amount = float(updates["amount"])
            difference = new_amount - old_amount

            if difference > 0:  # Increasing expense
                account = Account.objects.get(id=current_txn.account_id)
                if account.balance < difference:
                    return (
                        None,
                        f"Insufficient balance. Available: {float(account.balance):.2f}, Additional needed: {difference:.2f}",
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
                return None, "Expense not found"

            txn = (
                Transaction.objects.filter(id=expense_id)
                .values(*TRANSACTION_FIELDS)
                .first()
            )
            return txn, None
        except Exception as e:
            logger.exception("Failed to update expense")
            return None, str(e)

    result, error = await update_expense_record()
    if error:
        return error_response(error, code=404 if "not found" in error else 400)
    return success_response(format_transaction(result), "Expense updated successfully")


@router.delete("/{expense_id}", response=TransactionResponse)
async def delete_expense(request, expense_id: int):
    """Soft delete an expense. Refunds account balance."""

    # Complex transactional logic - keep in sync_to_async for atomicity
    @sync_to_async
    def soft_delete_expense():
        try:
            txn = Transaction.objects.filter(
                id=expense_id,
                user_id=request.user.id,
                transaction_type="EXPENSE",
                active=True,
            ).first()

            if not txn:
                return False, "Expense not found"

            # Refund balance
            if txn.account_id:
                account = Account.objects.get(id=txn.account_id)
                account.balance += txn.amount
                account.save(update_fields=["balance"])

            txn.active = False
            txn.updated_at = timezone.now()
            txn.save(update_fields=["active", "updated_at"])

            return True, None
        except Exception as e:
            logger.exception("Failed to delete expense")
            return False, str(e)

    success, error = await soft_delete_expense()
    if not success:
        return error_response(error, code=404 if "not found" in error else 500)
    return success_response(None, "Expense deleted successfully")

"""Transactions database operations - Generic CRUD (backward compatibility).

This module provides generic transaction endpoints that work with all types.
For type-specific operations, use:
- expenses.py for EXPENSE transactions
- transfers.py for TRANSFER transactions
- deposits.py for DEPOSIT transactions
"""

import logging
from typing import Optional

from ninja import Router, Query

from core.models import Transaction
from core.utils.responses import success_response, error_response
from .utils import TRANSACTION_FIELDS, format_transaction
from .schemas import TransactionResponse, TransactionListResponse
from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/", response=TransactionListResponse)
def get_transactions(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve all transactions for a user (all types)."""
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
        ordering = ("-date", "-created_at")

    transactions = queryset.order_by(*ordering).values(*TRANSACTION_FIELDS)[:limit]
    result = [format_transaction(txn) for txn in transactions]
    return success_response(result)


@router.get("/{transaction_id}", response=TransactionResponse)
def get_transaction(request, transaction_id: int):
    """Get a single transaction (any type)."""
    txn = (
        Transaction.objects.filter(id=transaction_id, user_id=request.user.id)
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Transaction not found", code=404)
    return success_response(format_transaction(txn))

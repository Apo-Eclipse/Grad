"""Transactions database operations."""

import logging
from typing import Any, Dict, Optional

from ninja import Router, Query
from django.db.models import Count

from django.utils import timezone

from core.models import Transaction
from core.utils.responses import success_response, error_response
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce

from .schemas import (
    TransactionCreateSchema,
    TransactionUpdateSchema,
    TransactionOutSchema,
    TransactionResponse,
    TransactionListResponse,
    TransactionSummarySchema,
)

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


@router.get("/summary", response=TransactionSummarySchema)
def get_transaction_summary(
    request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """
    Get total amount and count of transactions for a period.
    Only counts active expenses.
    """
    filters = {
        "user_id": request.user.id,
        "active": True,
        "transaction_type": "EXPENSE",
    }

    if start_date:
        filters["date__gte"] = start_date
    if end_date:
        filters["date__lte"] = end_date

    agg = Transaction.objects.filter(**filters).aggregate(
        total=Coalesce(Sum("amount"), 0, output_field=DecimalField()), count=Count("id")
    )

    return {
        "total_amount": float(agg["total"]),
        "currency": "EGP",
        "count": agg["count"],
    }


# Fields to retrieve for transaction queries
TRANSACTION_FIELDS = (
    "id",
    "user_id",
    "date",
    "amount",
    "time",
    "description",  # Was store_name
    "city",
    "category",  # Was type_spending
    "budget_id",
    "neighbourhood",
    "active",
    "created_at",
    "updated_at",
    "transaction_type",
    "account_id",
    "transfer_to_id",
)

TRANSACTION_FIELDS_WITH_BUDGET = TRANSACTION_FIELDS + (
    "budget__budget_name",
    "budget__description",
)


def _format_transaction(
    txn: Dict[str, Any], include_budget_name: bool = False
) -> Dict[str, Any]:
    """Format transaction dict for JSON response."""
    result = {
        "id": txn["id"],
        "user_id": txn["user_id"],
        "date": txn["date"],
        "amount": float(txn["amount"]) if txn["amount"] else 0.0,
        "time": str(txn["time"]) if txn["time"] else None,
        "description": txn.get("description"),
        "city": txn["city"],
        "category": txn.get("category"),
        "budget_id": txn["budget_id"],
        "neighbourhood": txn["neighbourhood"],
        "active": txn.get("active", True),
        "created_at": txn["created_at"],
        "updated_at": txn["updated_at"],
        "transaction_type": txn.get("transaction_type", "EXPENSE"),
        "account_id": txn.get("account_id"),
        "transfer_to_id": txn.get("transfer_to_id"),
    }

    # Budget Metadata (if requested)
    if include_budget_name and "budget__budget_name" in txn:
        if txn.get("budget__budget_name"):
            result["budget_name"] = txn["budget__budget_name"]
            result["budget_icon"] = txn.get("budget__icon")
            result["budget_color"] = txn.get("budget__color")
        # else: Unbudgeted, no budget metadata to add

    return result


@router.get("/", response=TransactionListResponse)
def get_transactions(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Retrieve transactions for a user."""
    # Build the filter arguments immediately
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

    # Sorting logic: If viewing 'deleted' items, sort by updated_at desc
    if active is False:
        ordering = ("-updated_at",)
    else:
        ordering = ("-date", "-time")

    transactions = queryset.order_by(*ordering).values(*TRANSACTION_FIELDS_WITH_BUDGET)[
        :limit
    ]

    result = [
        _format_transaction(txn, include_budget_name=True) for txn in transactions
    ]
    return success_response(result)


@router.post("/", response=TransactionResponse)
def create_transaction(request, payload: TransactionCreateSchema):
    """Create a new transaction row."""
    try:
        txn = Transaction.objects.create(
            user_id=request.user.id,
            date=payload.date,
            amount=payload.amount,
            time=payload.time,
            description=payload.description,  # Was store_name
            city=payload.city,
            category=payload.category,  # Was type_spending
            budget_id=payload.budget_id,
            neighbourhood=payload.neighbourhood,
            account_id=payload.account_id,
            transaction_type=payload.transaction_type,
        )
        # Return created transaction data using values
        created = (
            Transaction.objects.filter(id=txn.id).values(*TRANSACTION_FIELDS).first()
        )
        return success_response(
            _format_transaction(created), "Transaction created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create transaction")
        return error_response(f"Failed to create transaction: {e}")


@router.get("/{transaction_id}", response=TransactionResponse)
def get_transaction(request, transaction_id: int):
    """Get a single transaction."""
    txn = (
        Transaction.objects.filter(id=transaction_id, user_id=request.user.id)
        .values(*TRANSACTION_FIELDS_WITH_BUDGET)
        .first()
    )
    if not txn:
        return error_response("Transaction not found", code=404)
    return success_response(_format_transaction(txn, include_budget_name=True))


@router.put("/{transaction_id}", response=TransactionResponse)
def update_transaction(request, transaction_id: int, payload: TransactionUpdateSchema):
    """Update an existing transaction."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    # Manually update updated_at since using .update() bypasses auto_now
    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Transaction.objects.filter(
            id=transaction_id, user_id=request.user.id
        ).update(**updates)
        if rows_affected == 0:
            return error_response("Transaction not found", code=404)

        txn = (
            Transaction.objects.filter(id=transaction_id, user_id=request.user.id)
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
        rows_affected = Transaction.objects.filter(
            id=transaction_id, user_id=request.user.id
        ).update(active=False)
        if rows_affected == 0:
            return error_response("Transaction not found", code=404)

        return success_response(None, "Transaction deleted successfully")
    except Exception as e:
        logger.exception("Failed to delete transaction")
        return error_response(f"Failed to delete transaction: {e}")


@router.get("/search/", response=TransactionListResponse)
def search_transactions(
    request,
    query_text: Optional[str] = Query(None, alias="query"),
    category: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    neighbourhood: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Advanced transaction search."""
    queryset = Transaction.objects.filter(user_id=request.user.id)

    if query_text:
        queryset = queryset.filter(
            Q(description__icontains=query_text) | Q(category__icontains=query_text)
        )

    if category:
        queryset = queryset.filter(
            Q(category=category) | Q(budget__budget_name__icontains=category)
        )

    if min_amount is not None:
        queryset = queryset.filter(amount__gte=min_amount)

    if max_amount is not None:
        queryset = queryset.filter(amount__lte=max_amount)

    if start_date:
        queryset = queryset.filter(date__gte=start_date)

    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    if city:
        queryset = queryset.filter(city__icontains=city)

    if neighbourhood:
        queryset = queryset.filter(neighbourhood__icontains=neighbourhood)

    transactions = queryset.order_by("-date").values(*TRANSACTION_FIELDS_WITH_BUDGET)[
        :limit
    ]

    result = [
        _format_transaction(txn, include_budget_name=True) for txn in transactions
    ]
    return success_response(result, count=len(result))

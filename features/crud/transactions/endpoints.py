"""Transactions database operations."""

import logging
from typing import Any, Dict, Optional

from ninja import Router, Query
from django.db.models import Q

from core.models import Transaction
from core.utils.responses import success_response, error_response
from .schemas import TransactionCreateSchema, TransactionUpdateSchema

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
    "store_name",
    "city",
    "type_spending",
    "budget_id",
    "neighbourhood",
    "active",
    "created_at",
)

TRANSACTION_FIELDS_WITH_BUDGET = TRANSACTION_FIELDS + ("budget__budget_name",)


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
        "store_name": txn["store_name"],
        "city": txn["city"],
        "type_spending": txn["type_spending"],
        "budget_id": txn["budget_id"],
        "neighbourhood": txn["neighbourhood"],
        "active": txn.get("active", True),
        "created_at": txn["created_at"],
    }
    if include_budget_name and "budget__budget_name" in txn:
        result["budget_name"] = txn["budget__budget_name"]
    return result


@router.get("/", response=Dict[str, Any])
def get_transactions(
    request,
    active: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
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

    queryset = Transaction.objects.filter(**filters)

    transactions = queryset.order_by("-date", "-time").values(
        *TRANSACTION_FIELDS_WITH_BUDGET
    )[:limit]

    result = [
        _format_transaction(txn, include_budget_name=True) for txn in transactions
    ]
    return success_response(result)


@router.post("/", response=Dict[str, Any])
def create_transaction(request, payload: TransactionCreateSchema):
    """Create a new transaction row."""
    try:
        txn = Transaction.objects.create(
            user_id=request.user.id,
            date=payload.date,
            amount=payload.amount,
            time=payload.time,
            store_name=payload.store_name,
            city=payload.city,
            type_spending=payload.type_spending,
            budget_id=payload.budget_id,
            neighbourhood=payload.neighbourhood,
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


@router.get("/{transaction_id}", response=Dict[str, Any])
def get_transaction(request, transaction_id: int):
    """Get a single transaction."""
    txn = (
        Transaction.objects.filter(id=transaction_id, user_id=request.user.id)
        .values(*TRANSACTION_FIELDS)
        .first()
    )
    if not txn:
        return error_response("Transaction not found", code=404)
    return success_response(_format_transaction(txn))


@router.put("/{transaction_id}", response=Dict[str, Any])
def update_transaction(request, transaction_id: int, payload: TransactionUpdateSchema):
    """Update an existing transaction."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

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


@router.delete("/{transaction_id}", response=Dict[str, Any])
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


@router.get("/search/", response=Dict[str, Any])
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
            Q(store_name__icontains=query_text) | Q(type_spending__icontains=query_text)
        )

    if category:
        queryset = queryset.filter(
            Q(type_spending=category) | Q(budget__budget_name__icontains=category)
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

"""Shared utilities for transaction endpoints."""

from typing import Any, Dict

# Fields to retrieve for transaction queries
TRANSACTION_FIELDS = (
    "id",
    "user_id",
    "date",
    "amount",
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


def format_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Format transaction dict for JSON response."""
    return {
        "id": txn["id"],
        "user_id": txn["user_id"],
        "date": txn["date"],
        "amount": float(txn["amount"]) if txn["amount"] else 0.0,
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

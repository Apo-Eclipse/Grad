"""Shared transaction schemas for response validation."""

from typing import Any, Optional
from datetime import date
from ninja import Schema


class TransactionOutSchema(Schema):
    """Base output schema for all transaction types."""

    id: int
    user_id: int
    date: date
    amount: float
    description: Optional[str] = None
    city: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    account_id: Optional[int] = None
    transfer_to_id: Optional[int] = None
    transaction_type: str
    active: bool
    created_at: Any
    updated_at: Any


class TransactionResponse(Schema):
    """Single transaction response wrapper."""

    status: str
    message: str
    data: Optional[TransactionOutSchema] = None


class TransactionListResponse(Schema):
    """List of transactions response wrapper."""

    status: str
    message: str
    data: list[TransactionOutSchema]

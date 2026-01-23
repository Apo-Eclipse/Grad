from typing import Any, Dict, Optional
from datetime import date
from ninja import Schema
from pydantic import model_validator


class TransactionCreateSchema(Schema):
    date: date
    amount: float
    time: Optional[str] = None
    description: Optional[str] = None  # Was store_name
    city: Optional[str] = None
    category: Optional[str] = None  # Was type_spending
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    account_id: Optional[int] = None  # Link to Account
    transaction_type: str = "EXPENSE"  # EXPENSE or TRANSFER


class TransactionUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    time: Optional[str] = None
    description: Optional[str] = None  # Was store_name
    city: Optional[str] = None
    category: Optional[str] = None  # Was type_spending
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    active: Optional[bool] = None
    account_id: Optional[int] = None  # Link to Account

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


class TransactionOutSchema(Schema):
    id: int
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    active: bool
    created_at: Any
    updated_at: Any
    transaction_type: str
    account_id: Optional[int] = None
    transfer_to_id: Optional[int] = None
    # Optional Budget Metadata
    budget_name: Optional[str] = None
    budget_icon: Optional[str] = None
    budget_color: Optional[str] = None


class TransactionResponse(Schema):
    status: str
    message: str
    data: Optional[TransactionOutSchema] = None


class TransactionListResponse(Schema):
    status: str
    message: str
    data: list[TransactionOutSchema]
    count: Optional[int] = None


class TransactionSummarySchema(Schema):
    total_amount: float
    currency: str
    count: int

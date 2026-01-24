from typing import Any, Optional
from datetime import date
from ninja import Schema
from pydantic import model_validator


class TransactionCreateSchema(Schema):
    date: date
    amount: float
    time: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    account_id: Optional[int] = None
    transaction_type: str = "EXPENSE"


class TransactionUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    time: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    active: Optional[bool] = None
    account_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values


# Base CRUD output (raw data only)
class TransactionOutSchema(Schema):
    id: int
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None
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
    status: str
    message: str
    data: Optional[TransactionOutSchema] = None


class TransactionListResponse(Schema):
    status: str
    message: str
    data: list[TransactionOutSchema]

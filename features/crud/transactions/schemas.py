from typing import Any, Dict, Optional
from datetime import date, datetime

from ninja import Schema
from pydantic import root_validator


class TransactionSchema(Schema):
    id: int
    user_id: int
    date: date
    amount: float
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    created_at: datetime


class TransactionCreateSchema(Schema):
    date: date
    amount: float
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None


class TransactionUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    time: Optional[str] = None
    store_name: Optional[str] = None
    city: Optional[str] = None
    type_spending: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

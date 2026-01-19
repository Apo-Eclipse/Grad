from typing import Any, Dict, Optional
from datetime import date
from ninja import Schema
from pydantic import root_validator


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

    @root_validator(pre=True)
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

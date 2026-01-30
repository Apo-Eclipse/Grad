"""Transfer transaction schemas."""

from typing import Optional
from datetime import date
from ninja import Schema


class TransferCreateSchema(Schema):
    from_account_id: int
    to_account_id: int
    amount: float
    date: Optional[date] = None
    description: Optional[str] = None

"""Deposit transaction schemas."""

from typing import Optional
from datetime import date
from ninja import Schema
from pydantic import model_validator


class DepositCreateSchema(Schema):
    date: date
    amount: float
    description: Optional[str] = None
    account_id: Optional[int] = None


class DepositUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    account_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

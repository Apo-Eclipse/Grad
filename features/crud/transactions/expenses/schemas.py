"""Expense transaction schemas."""

from typing import Optional
from datetime import date
from ninja import Schema
from pydantic import model_validator


class ExpenseCreateSchema(Schema):
    date: date
    amount: float
    description: Optional[str] = None
    city: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    account_id: Optional[int] = None


class ExpenseUpdateSchema(Schema):
    date: Optional[date] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    city: Optional[str] = None
    budget_id: Optional[int] = None
    neighbourhood: Optional[str] = None
    account_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, values):
        if not values:
            raise ValueError("At least one field must be provided for update.")
        return values

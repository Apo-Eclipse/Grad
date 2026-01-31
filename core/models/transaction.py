"""Transaction model."""

from django.db import models
from django.contrib.auth.models import User
from .budget import Budget
from .account import Account


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        EXPENSE = "EXPENSE", "Expense"
        TRANSFER = "TRANSFER", "Transfer"
        DEPOSIT = "DEPOSIT", "Deposit"

    transaction_type = models.TextField(
        choices=TransactionType.choices, default=TransactionType.EXPENSE
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)  # Was store_name
    city = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    budget = models.ForeignKey(
        Budget, models.DO_NOTHING, blank=True, null=True
    )  # Now nullable
    account = models.ForeignKey(
        Account, models.DO_NOTHING, blank=True, null=True, related_name="transactions"
    )
    transfer_to = models.ForeignKey(
        Account, models.DO_NOTHING, blank=True, null=True, related_name="transfers_in"
    )
    income_source = models.ForeignKey(
        "core.Income",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="transactions",
    )
    neighbourhood = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"

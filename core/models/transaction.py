"""Transaction model."""

from django.db import models
from django.contrib.auth.models import User
from .budget import Budget
from .account import Account


class Transaction(models.Model):
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    time = models.TimeField(blank=True, null=True)
    store_name = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    type_spending = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    budget = models.ForeignKey(Budget, models.DO_NOTHING)
    account = models.ForeignKey(
        Account, models.DO_NOTHING, blank=True, null=True, related_name="transactions"
    )
    transfer_to = models.ForeignKey(
        Account, models.DO_NOTHING, blank=True, null=True, related_name="transfers_in"
    )
    neighbourhood = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"

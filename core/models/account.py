"""Account model."""

from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    class AccountType(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        SAVINGS = "SAVINGS", "Savings"
        CREDIT = "CREDIT", "Credit"

    user = models.ForeignKey(User, models.DO_NOTHING)
    name = models.TextField()
    type = models.TextField(choices=AccountType.choices, default=AccountType.REGULAR)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"

"""Income model."""

from django.db import models
from django.contrib.auth.models import User


from .account import Account


class Income(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    account = models.ForeignKey(Account, models.DO_NOTHING, blank=True, null=True)
    type_income = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    payment_day = models.IntegerField(blank=True, null=True)
    next_payment_date = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"

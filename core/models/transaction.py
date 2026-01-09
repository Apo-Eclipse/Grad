"""Transaction model."""

from django.db import models
from django.contrib.auth.models import User
from .budget import Budget


class Transaction(models.Model):
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    time = models.TimeField(blank=True, null=True)
    store_name = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    type_spending = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    budget = models.ForeignKey(Budget, models.DO_NOTHING)
    neighbourhood = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"

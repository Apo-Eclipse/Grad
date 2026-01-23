"""Budget model."""

from django.db import models
from django.contrib.auth.models import User


class Budget(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    budget_name = models.TextField()
    description = models.TextField(blank=True, null=True)
    total_limit = models.DecimalField(max_digits=12, decimal_places=2)
    priority_level_int = models.SmallIntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)
    icon = models.TextField(default="cash-outline")
    color = models.TextField(default="#10b981")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"

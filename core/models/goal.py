"""Goal model."""

from django.db import models
from django.contrib.auth.models import User


class Goal(models.Model):
    goal_name = models.TextField()
    description = models.TextField(blank=True, null=True)
    target = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING)
    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)

    class Meta:
        app_label = "core"

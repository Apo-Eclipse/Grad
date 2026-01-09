"""User and Profile models."""

from django.db import models
from django.contrib.auth.models import User
from typing import Dict


EMPLOYMENT_OPTIONS: Dict[str, str] = {
    "1": "Employed Full-time",
    "2": "Employed Part-time",
    "3": "Unemployed",
    "4": "Retired",
}

EDUCATION_OPTIONS: Dict[str, str] = {
    "1": "High school",
    "2": "Associate degree",
    "3": "Bachelor degree",
    "4": "Masters Degree",
    "5": "PhD",
}

GENDER_OPTIONS: Dict[str, str] = {
    "1": "male",
    "2": "female",
}


class Profile(models.Model):
    user = models.OneToOneField(User, models.DO_NOTHING)
    job_title = models.TextField(blank=True, null=True)
    address = models.TextField()
    birthday = models.DateField()
    gender = models.TextField(blank=True, null=True, choices=GENDER_OPTIONS.items())
    employment_status = models.TextField(
        blank=True, null=True, choices=EMPLOYMENT_OPTIONS.items()
    )
    education_level = models.TextField(
        blank=True, null=True, choices=EDUCATION_OPTIONS.items()
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    user_persona = models.JSONField(blank=True, null=True)

    class Meta:
        app_label = "core"

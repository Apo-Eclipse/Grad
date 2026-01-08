# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
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


class Budget(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    budget_name = models.TextField()
    description = models.TextField(blank=True, null=True)
    total_limit = models.DecimalField(max_digits=12, decimal_places=2)
    priority_level_int = models.SmallIntegerField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)


class ChatConversation(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    title = models.TextField(blank=True, null=True)
    channel = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    summary_text = models.TextField(blank=True, null=True)
    summary_created_at = models.DateTimeField(blank=True, null=True)


class ChatMessage(models.Model):
    conversation = models.ForeignKey(ChatConversation, models.DO_NOTHING)
    sender_type = models.TextField()
    source_agent = models.TextField()
    content = models.TextField()
    content_type = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


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


class Income(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    type_income = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)


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

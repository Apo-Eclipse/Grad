"""Chat conversation and message models."""

from django.db import models
from django.contrib.auth.models import User


class ChatConversation(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING)
    title = models.TextField(blank=True, null=True)
    channel = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    summary_text = models.TextField(blank=True, null=True)
    summary_created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "core"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(ChatConversation, models.DO_NOTHING)
    sender_type = models.TextField()
    source_agent = models.TextField()
    content = models.TextField()
    content_type = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"

"""Admin configuration for core models."""

from django.contrib import admin
from .models import (
    Profile,
    Budget,
    Transaction,
    Goal,
    Income,
    ChatConversation,
    ChatMessage,
)

# Register models
admin.site.register(Profile)
admin.site.register(Budget)
admin.site.register(Transaction)
admin.site.register(Goal)
admin.site.register(Income)
admin.site.register(ChatConversation)
admin.site.register(ChatMessage)

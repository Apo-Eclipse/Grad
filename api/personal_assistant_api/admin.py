"""Django admin configuration."""
from django.contrib import admin
from .models import *  # Import your model

# Register the model
# admin.site.register(Users)
admin.site.register(Transaction)
admin.site.register(Profile)
admin.site.register(Income)
admin.site.register(Goal)
admin.site.register(ChatMessage)
admin.site.register(ChatConversation)
admin.site.register(Budget)
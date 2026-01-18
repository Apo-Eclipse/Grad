from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from core.models import Notification
from .schemas import NotificationSchema
from features.auth.api import AuthBearer

router = Router(auth=AuthBearer())

@router.get("/", response=List[NotificationSchema])
def list_notifications(request):
    """List all notifications for the user, ordered by newest first."""
    return Notification.objects.filter(user=request.user).order_by("-created_at")

@router.put("/{notification_id}/read", response={200: str})
def mark_as_read(request, notification_id: int):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return "Marked as read"

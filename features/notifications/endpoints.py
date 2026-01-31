from typing import List

from ninja import Router
from core.models import Notification
from .schemas import NotificationSchema
from features.auth.api import AuthBearer

router = Router(auth=AuthBearer())


@router.get("/", response=List[NotificationSchema])
async def list_notifications(request):
    """List all notifications for the user, ordered by newest first."""
    notifications = [
        n
        async for n in Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )
    ]
    return notifications


@router.put("/{notification_id}/read", response={200: str})
async def mark_as_read(request, notification_id: int):
    """Mark a notification as read."""
    try:
        notification = await Notification.objects.aget(
            id=notification_id, user=request.user
        )
        notification.is_read = True
        await notification.asave()
        return "Marked as read"
    except Notification.DoesNotExist:
        return 404, "Notification not found"

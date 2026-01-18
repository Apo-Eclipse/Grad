from datetime import datetime
from ninja import Schema

class NotificationSchema(Schema):
    id: int
    title: str
    message: str
    is_read: bool
    notification_type: str
    created_at: datetime

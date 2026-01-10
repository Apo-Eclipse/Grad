from datetime import datetime
from typing import Optional


from ninja import Schema
from pydantic import Field


class ConversationStartSchema(Schema):
    user_id: int
    channel: str = Field(default="web")


class ConversationResponseSchema(Schema):
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime


class ConversationSchema(Schema):
    conversation_id: int
    user_id: int
    title: Optional[str] = None
    channel: Optional[str] = None
    started_at: datetime
    last_message_at: Optional[datetime] = None


class MessageSchema(Schema):
    message_id: int
    conversation_id: int
    sender_type: str
    content: str
    content_type: str
    created_at: datetime

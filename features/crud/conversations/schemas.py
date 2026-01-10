from datetime import datetime


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

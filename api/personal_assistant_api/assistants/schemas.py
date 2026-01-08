"""Schemas specific to the Personal Assistant agents."""
from datetime import datetime
from typing import Any, Dict, Optional

from ninja import Schema
from pydantic import Field


class AnalysisRequestSchema(Schema):
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


class AnalysisResponseSchema(Schema):
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(Schema):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationStartSchema(Schema):
    user_id: int
    channel: str = Field(default="web")


class ConversationResponseSchema(Schema):
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime

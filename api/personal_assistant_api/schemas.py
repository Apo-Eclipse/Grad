"""Request and response schemas."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AnalysisRequestSchema(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


class AnalysisResponseSchema(BaseModel):
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(BaseModel):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationStartSchema(BaseModel):
    user_id: int
    channel: str = Field(default="web")


class ConversationResponseSchema(BaseModel):
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime

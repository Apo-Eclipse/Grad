"""Request and response schemas."""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class AnalysisRequestSchema(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


class AnalysisResponseSchema(BaseModel):
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(BaseModel):
    error: str
    message: str
    timestamp: datetime


class ConversationStartSchema(BaseModel):
    user_id: int
    channel: Optional[str] = "web"


class ConversationResponseSchema(BaseModel):
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime


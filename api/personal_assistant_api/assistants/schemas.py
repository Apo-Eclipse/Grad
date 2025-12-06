"""Schemas for the Personal Assistant module."""
from ninja import Schema
from pydantic import Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class AnalysisRequestSchema(Schema):
    """Request schema for the analyze endpoint."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


class AnalysisResponseSchema(Schema):
    """Response schema for the analyze endpoint."""
    final_output: str
    data: Optional[Any] = None
    conversation_id: Optional[int] = None


class AnalysisErrorSchema(Schema):
    """Error response schema."""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationStartSchema(Schema):
    """Schema for starting a new conversation."""
    user_id: int
    channel: str = Field(default="web")


class ConversationResponseSchema(Schema):
    """Response schema for conversation start."""
    conversation_id: int
    user_id: int
    channel: str
    started_at: datetime


"""
Request and response schemas for the Personal Assistant API.
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class AnalysisRequestSchema(BaseModel):
    """Schema for submitting an analysis request."""
    
    query: str = Field(..., description="The main analysis query")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for the analysis"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the request"
    )


class AnalysisStatusSchema(BaseModel):
    """Schema for checking analysis status."""
    
    request_id: str = Field(..., description="Unique request identifier")


class AnalysisStepsSchema(BaseModel):
    """Schema for analysis steps information."""
    
    step_name: str
    status: str
    timestamp: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None


class AnalysisResponseSchema(BaseModel):
    """Schema for analysis response."""
    
    request_id: str
    status: str
    query: str
    steps: List[AnalysisStepsSchema]
    database_results: Dict[str, Any]
    explanations: Dict[str, Any]
    analysis_output: Dict[str, Any]
    processing_time_ms: Optional[int]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AnalysisErrorSchema(BaseModel):
    """Schema for error responses."""
    
    request_id: Optional[str] = None
    error: str
    message: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class AnalysisStatusResponseSchema(BaseModel):
    """Schema for status check response."""
    
    request_id: str
    status: str
    query: str
    created_at: datetime
    completed_at: Optional[datetime]
    processing_time_ms: Optional[int]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class AnalysisHistorySchema(BaseModel):
    """Schema for analysis history entry."""
    
    request_id: str
    status: str
    query: str
    created_at: datetime
    completed_at: Optional[datetime]
    processing_time_ms: Optional[int]
    
    class Config:
        from_attributes = True


class BulkAnalysisRequestSchema(BaseModel):
    """Schema for bulk analysis requests."""
    
    queries: List[str] = Field(..., description="List of queries to analyze")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for all analyses"
    )


class BulkAnalysisResponseSchema(BaseModel):
    """Schema for bulk analysis response."""
    
    batch_id: str
    total_requests: int
    request_ids: List[str]
    created_at: datetime

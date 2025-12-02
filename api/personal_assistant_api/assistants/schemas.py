from ninja import Schema
from typing import List, Optional, Dict, Any

class AnalysisRequestSchema(Schema):
    user_id: int
    user_prompt: str
    current_date: str

class AnalysisResponseSchema(Schema):
    response: str
    data: Optional[Dict[str, Any]] = None

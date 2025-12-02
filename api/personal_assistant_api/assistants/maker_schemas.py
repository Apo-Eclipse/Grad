from ninja import Schema
from typing import Optional

class MakerRequestSchema(Schema):
    user_id: int
    request: str
    current_date: str

class MakerResponseSchema(Schema):
    response: str
    status: str = "success"

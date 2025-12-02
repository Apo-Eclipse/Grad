from ninja import Schema
from typing import Any, Optional

def success_response(data: Any = None, message: str = "Success"):
    return {"status": "success", "message": message, "data": data}

def error_response(message: str, code: int = 400):
    return {"status": "error", "message": message, "code": code}

def data_response(data: Any):
    return data

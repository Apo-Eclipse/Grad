"""Standardized API response helpers."""

from typing import Any, Dict, Optional


def success_response(
    data: Any = None, message: str = "Success", count: Optional[int] = None
) -> Dict[str, Any]:
    """Return a standardized success response."""
    response = {"status": "success", "message": message, "data": data}
    if count is not None:
        response["count"] = count
    return response


def error_response(message: str, code: int = 400) -> Dict[str, Any]:
    """Return a standardized error response."""
    return {"status": "error", "message": message, "code": code}


def data_response(data: Any) -> Any:
    """Return raw data response (useful for simple list/dict returns)."""
    return data

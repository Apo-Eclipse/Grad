"""Core database utilities."""

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import connection

logger = logging.getLogger(__name__)


# ============================================================================
# Raw SQL utilities - kept for admin/debug endpoints (/execute/*)
# ============================================================================


def dictfetchall(cursor) -> List[Dict[str, Any]]:
    """Convert database cursor results to list of dicts."""
    if not cursor.description:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def run_select(
    query: str, params: Optional[List[Any]] = None, log_name: str = "query"
) -> List[Dict[str, Any]]:
    """Execute a read-only query and return list of dicts."""
    params = list(params or [])
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return dictfetchall(cursor)
    except Exception:
        logger.exception("Error executing %s", log_name)
        return []


def execute_modify(
    query: str, params: Optional[List[Any]] = None, log_name: str = "modify"
) -> int:
    """Execute a write query (INSERT/UPDATE/DELETE) and return rowcount."""
    params = list(params or [])
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
        connection.commit()
        return rows_affected
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        logger.exception("Error executing %s", log_name)
        return 0


# ============================================================================
# JSON utilities
# ============================================================================


def safe_json_body(request) -> Dict[str, Any]:
    """Parse JSON request body safely."""
    try:
        raw = request.body or b"{}"
        return json.loads(raw)
    except Exception:
        logger.debug("Received invalid JSON body", exc_info=True)
        return {}


def decimal_to_float(value: Any) -> float:
    """Convert Decimal-compatible values to floats for JSON serialization."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def serialize_decimals(data: Any) -> Any:
    """Recursively convert Decimals to floats in a data structure."""
    if isinstance(data, dict):
        return {k: serialize_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_decimals(i) for i in data]
    elif isinstance(data, Decimal):
        return float(data)
    return data

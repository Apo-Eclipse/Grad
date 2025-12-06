from django.db import connection
from ninja.errors import HttpError
import json
import decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def dictfetchone(cursor):
    "Return one row from a cursor as a dict"
    desc = cursor.description
    if desc is None:
        return None
    columns = [col[0] for col in desc]
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def run_select(sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return list of dicts."""
    params = list(params or [])
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return dictfetchall(cursor)
    except Exception as exc:
        logger.exception("Error executing SELECT query")
        return []


def run_select_single(
    sql: str,
    params: Optional[List[Any]] = None,
    default: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a SELECT query and return a single dict result."""
    params = list(params or [])
    fallback = default if default is not None else {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = dictfetchall(cursor)
            return rows[0] if rows else fallback
    except Exception as exc:
        logger.exception("Error executing SELECT query")
        return fallback


def execute_modify(sql: str, params: Optional[List[Any]] = None) -> int:
    """Execute INSERT/UPDATE/DELETE and return rowcount."""
    params = list(params or [])
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            connection.commit()
            return cursor.rowcount
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        logger.exception("Error executing modify query")
        return 0


def execute_modify_returning(
    sql: str,
    params: List[Any],
    log_name: str = "query",
) -> Tuple[bool, int, Optional[Dict[str, Any]]]:
    """Execute a write query with RETURNING clause and return (success, rows_affected, returned_row)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = dictfetchone(cursor) if cursor.description else None
            rows_affected = cursor.rowcount
        connection.commit()
        return True, rows_affected, row
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            logger.debug("Rollback failed after %s", log_name, exc_info=True)
        logger.exception("Error executing %s", log_name)
        return False, 0, None


def decimal_to_float(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def safe_json_body(request) -> Dict[str, Any]:
    """Parse JSON request body safely."""
    try:
        raw = request.body or b"{}"
        return json.loads(raw)
    except Exception:
        logger.debug("Received invalid JSON body", exc_info=True)
        return {}


def serialize_decimals(data):
    """Helper to serialize data with decimals to JSON compatible dict/list"""
    return json.loads(json.dumps(data, default=decimal_to_float))


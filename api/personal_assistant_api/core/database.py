from django.db import connection
from ninja.errors import HttpError
import json
import decimal

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

def run_select(sql, params=None):
    """Execute a SELECT query and return list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return dictfetchall(cursor)

def execute_modify(sql, params=None):
    """Execute INSERT/UPDATE/DELETE and return rowcount."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount

def decimal_to_float(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

def safe_json_body(data):
    """Helper to serialize data with decimals to JSON compatible dict/list"""
    return json.loads(json.dumps(data, default=decimal_to_float))

"""
API endpoints for the Personal Assistant.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from ninja import Router, Query
from ninja.responses import NinjaJSONEncoder
import asyncio
from asgiref.sync import sync_to_async
import json

from .schemas import (
    AnalysisRequestSchema,
    AnalysisResponseSchema,
    AnalysisErrorSchema,
    AnalysisStatusResponseSchema,
    AnalysisStatusSchema,
    AnalysisHistorySchema,
    BulkAnalysisRequestSchema,
    BulkAnalysisResponseSchema,
)
from .services import get_analyst_service
from .database import get_database

logger = logging.getLogger(__name__)
router = Router()

# Get service instances
analyst_service = get_analyst_service()
db = get_database()


class JSONEncoder(NinjaJSONEncoder):
    """Custom JSON encoder for handling various data types including Decimal."""
    
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Decimal):
            # Convert Decimal to float for JSON serialization
            return float(o)
        return super().default(o)


def convert_decimals(obj):
    """
    Recursively convert Decimal objects to float for JSON serialization.
    Handles nested dicts and lists.
    """
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def make_json_serializable(obj):
    """Recursively convert objects that are not JSON serializable into
    basic Python types (str, int, float, list, dict).

    Handles:
    - datetime and pandas.Timestamp -> ISO string
    - Decimal -> float
    - numpy scalars/arrays -> native Python types
    - pandas Series/DataFrame -> lists/dicts
    - sets/tuples -> lists
    Falls back to str() for unknown types to avoid serialization failures.
    """
    from datetime import datetime
    from decimal import Decimal

    # Avoid importing heavy libs at module import time; import when needed
    pd = None
    np = None
    try:
        import pandas as _pd
        pd = _pd
    except Exception:
        pd = None
    try:
        import numpy as _np
        np = _np
    except Exception:
        np = None

    # Inner recursive function
    def _convert(o):
        # Basic containers
        if isinstance(o, dict):
            return {k: _convert(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_convert(i) for i in o]
        if isinstance(o, tuple) or isinstance(o, set):
            return [_convert(i) for i in list(o)]

        # Decimal -> float
        if isinstance(o, Decimal):
            try:
                return float(o)
            except Exception:
                return str(o)

        # datetime-like -> ISO string
        if isinstance(o, datetime):
            return o.isoformat()

        # pandas types
        if pd is not None:
            try:
                if isinstance(o, pd.Timestamp):
                    return o.isoformat()
                if isinstance(o, pd.Timedelta):
                    return str(o)
                if isinstance(o, pd.Series):
                    return _convert(o.tolist())
                if isinstance(o, pd.DataFrame):
                    # Convert DataFrame to list of records
                    try:
                        return _convert(o.to_dict(orient='records'))
                    except Exception:
                        return str(o)
            except Exception:
                # If pandas' internals raise, fall through to other checks
                pass

        # numpy types
        if np is not None:
            try:
                if isinstance(o, (np.integer, np.int64, np.int32)):
                    return int(o)
                if isinstance(o, (np.floating, np.float64, np.float32)):
                    return float(o)
                if isinstance(o, np.ndarray):
                    return _convert(o.tolist())
            except Exception:
                pass

        # Fallbacks for basic JSON types
        if isinstance(o, (str, int, float, bool)) or o is None:
            return o

        # As last resort, return string representation
        try:
            return str(o)
        except Exception:
            return None

    return _convert(obj)


@router.post(
    "submit",
    response={
        201: Dict[str, Any],
        400: AnalysisErrorSchema,
        500: AnalysisErrorSchema
    },
    summary="Submit a personal assistant request",
    description="Submit a new personal assistant request"
)
async def submit_analysis(request, payload: AnalysisRequestSchema):
    """
    Submit a new personal assistant request.
    
    - **query**: The main request query (required)
    - **filters**: Optional filters for the request
    - **metadata**: Optional metadata about the request
    
    Returns the request ID and status.
    """
    try:
        if not payload.query or not payload.query.strip():
            return 400, {
                "error": "INVALID_QUERY",
                "message": "Query cannot be empty",
                "timestamp": datetime.now()
            }
        
        # Create request in database (auto-generates request_id)
        db_request = await sync_to_async(db.create_request)(
            query=payload.query,
            filters=payload.filters,
            metadata=payload.metadata,
            status="pending"
        )
        request_id = db_request.request_id
        
        logger.info(f"Personal Assistant request submitted: {request_id}")
        
        return 201, {
            "request_id": request_id,
            "status": "pending",
            "query": payload.query,
            "created_at": db_request.created_at.isoformat() if db_request.created_at else datetime.now().isoformat(),
            "message": "Personal assistant request submitted successfully. Use the request_id to check status and retrieve results."
        }
    
    except Exception as e:
        logger.error(f"Error submitting personal assistant request: {str(e)}", exc_info=True)
        return 500, {
            "error": "SUBMISSION_ERROR",
            "message": f"Failed to submit personal assistant request: {str(e)}",
            "timestamp": datetime.now()
        }


@router.post(
    "analyze",
    response={
        200: Dict[str, Any],
        400: AnalysisErrorSchema,
        500: AnalysisErrorSchema
    },
    summary="Run personal assistant request and wait for results",
    description="Submit and wait for personal assistant request completion (synchronous)"
)
async def run_analysis_sync(request, payload: AnalysisRequestSchema):
    """
    Submit personal assistant request and wait for results synchronously.
    
    This endpoint will wait for the request to complete and return results directly.
    Use this for simpler queries or when you need immediate results.
    
    - **query**: The main request query (required)
    - **filters**: Optional filters for the request
    - **metadata**: Optional metadata about the request
    """
    try:
        if not payload.query or not payload.query.strip():
            return 400, {
                "error": "INVALID_QUERY",
                "message": "Query cannot be empty",
                "timestamp": datetime.now()
            }
        
        logger.info(f"Running personal assistant request: {payload.query}")
        
        # Create request record FIRST (so request_id exists)
        analysis_request = await sync_to_async(db.create_request)(
            query=payload.query,
            filters=payload.filters,
            metadata=payload.metadata,
            status="processing"
        )
        request_id = analysis_request.request_id
        
        # Run personal assistant request with request_id
        result = await analyst_service.run_analysis(
            query=payload.query,
            filters=payload.filters,
            metadata=payload.metadata,
            request_id=request_id
        )
        
        # Convert Decimals in result for JSON serialization
        result = convert_decimals(result)
        # Ensure all datetimes / pandas/numpy types are converted before DB save
        result = make_json_serializable(result)

        # Save result to database (async-safe wrapper)
        if result.get("status") == "completed":
            await sync_to_async(db.update_request_status)(
                request_id=request_id,
                status="completed",
                response_data=result
            )
            
            # Extract insights
            insights = []
            if result.get("analysis_output"):
                insights = result["analysis_output"].get("insights", [])
            
            # Save detailed result (async-safe wrapper)
            await sync_to_async(db.save_analysis_result)(
                request_id=request_id,
                steps_data=result.get("steps", {}),
                database_results=result.get("database_results", {}),
                explanations=result.get("explanations", {}),
                analysis_output=result.get("analysis_output", {}),
                insights=insights,
                summary=result.get("summary")
            )
        else:
            await sync_to_async(db.update_request_status)(
                request_id=request_id,
                status="failed",
                error_message=result.get("error")
            )
        
        return 200, result
    
    except Exception as e:
        logger.error(f"Error running personal assistant request: {str(e)}", exc_info=True)
        return 500, {
            "error": "ANALYSIS_ERROR",
            "message": f"Failed to run personal assistant request: {str(e)}",
            "timestamp": datetime.now()
        }


@router.post(
    "bulk",
    response={
        200: Dict[str, Any],
        400: AnalysisErrorSchema,
        500: AnalysisErrorSchema
    },
    summary="Run multiple personal assistant requests",
    description="Submit multiple queries for personal assistant processing in parallel"
)
async def run_bulk_analysis(request, payload: BulkAnalysisRequestSchema):
    """
    Run multiple personal assistant requests in parallel.
    
    - **queries**: List of queries to process (required)
    - **filters**: Optional filters for all requests
    
    Returns results for all queries.
    """
    try:
        if not payload.queries or len(payload.queries) == 0:
            return 400, {
                "error": "INVALID_QUERIES",
                "message": "At least one query is required",
                "timestamp": datetime.now()
            }
        
        if len(payload.queries) > 100:
            return 400, {
                "error": "TOO_MANY_QUERIES",
                "message": "Maximum 100 queries allowed per bulk request",
                "timestamp": datetime.now()
            }
        
        logger.info(f"Running bulk personal assistant requests with {len(payload.queries)} queries")
        
        result = await analyst_service.run_bulk_analysis(
            queries=payload.queries,
            filters=payload.filters
        )
        
        return 200, result
    
    except Exception as e:
        logger.error(f"Error running bulk personal assistant requests: {str(e)}", exc_info=True)
        return 500, {
            "error": "BULK_ANALYSIS_ERROR",
            "message": f"Failed to run bulk personal assistant requests: {str(e)}",
            "timestamp": datetime.now()
        }


@router.post(
    "status",
    response={
        200: AnalysisStatusResponseSchema,
        404: AnalysisErrorSchema,
        500: AnalysisErrorSchema
    },
    summary="Check personal assistant request status",
    description="Check the status of a submitted personal assistant request"
)
def check_status(request, payload: AnalysisStatusSchema):
    """
    Check the status of a personal assistant request.
    
    - **request_id**: The request ID returned from submit or analyze endpoint
    
    Returns the current status and any available results.
    """
    try:
        analysis_request = db.get_request(payload.request_id)
        
        if not analysis_request:
            return 404, {
                "error": "NOT_FOUND",
                "message": f"Personal assistant request {payload.request_id} not found",
                "timestamp": datetime.now()
            }
        
        response_data = {
            "request_id": analysis_request.request_id,
            "status": analysis_request.status,
            "query": analysis_request.query,
            "created_at": analysis_request.created_at,
            "completed_at": analysis_request.completed_at,
            "processing_time_ms": analysis_request.processing_time_ms,
            "error_message": analysis_request.error_message
        }
        
        return 200, response_data
    
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}", exc_info=True)
        return 500, {
            "error": "STATUS_CHECK_ERROR",
            "message": f"Failed to check status: {str(e)}",
            "timestamp": datetime.now()
        }


@router.get(
    "result/{request_id}",
    response={
        200: Dict[str, Any],
        404: AnalysisErrorSchema,
        500: AnalysisErrorSchema
    },
    summary="Get personal assistant request results",
    description="Retrieve the full results of a completed personal assistant request"
)
def get_results(request, request_id: str):
    """
    Get the full results of a completed personal assistant request.
    
    - **request_id**: The request ID from submit or analyze endpoint
    
    Returns the complete request results including database data, explanations, and insights.
    """
    try:
        analysis_request = db.get_request(request_id)
        
        if not analysis_request:
            return 404, {
                "error": "NOT_FOUND",
                "message": f"Personal assistant request {request_id} not found",
                "timestamp": datetime.now()
            }
        
        if analysis_request.status != "completed":
            return 404, {
                "error": "NOT_COMPLETED",
                "message": f"Personal assistant request is still {analysis_request.status}",
                "timestamp": datetime.now()
            }
        
        # Get detailed results
        result = db.get_analysis_result(request_id)
        
        response_data = {
            "request_id": request_id,
            "status": analysis_request.status,
            "query": analysis_request.query,
            "created_at": analysis_request.created_at,
            "completed_at": analysis_request.completed_at,
            "processing_time_ms": analysis_request.processing_time_ms,
            "response": analysis_request.response_data or {}
        }
        
        if result:
            response_data.update({
                "steps": result.steps_data,
                "database_results": result.database_results,
                "explanations": result.explanations,
                "analysis_output": result.analysis_output,
                "insights": result.insights,
                "summary": result.summary
            })
        
        return 200, response_data
    
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}", exc_info=True)
        return 500, {
            "error": "RETRIEVAL_ERROR",
            "message": f"Failed to retrieve results: {str(e)}",
            "timestamp": datetime.now()
        }


@router.get(
    "history",
    response={
        200: Dict[str, Any],
        500: AnalysisErrorSchema
    },
    summary="Get personal assistant request history",
    description="Get the history of submitted personal assistant requests"
)
def get_history(
    request,
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None),
    days: Optional[int] = Query(None)
):
    """
    Get personal assistant request history.
    
    Query Parameters:
    - **limit**: Maximum number of results to return (default: 50, max: 500)
    - **status**: Filter by status (pending, processing, completed, failed)
    - **days**: Filter to requests from last N days
    
    Returns a list of recent personal assistant requests.
    """
    try:
        requests = db.get_request_history(limit=limit, status=status, days=days)
        
        history = [
            {
                "request_id": r.request_id,
                "status": r.status,
                "query": r.query,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
                "processing_time_ms": r.processing_time_ms
            }
            for r in requests
        ]
        
        return 200, {
            "total": len(history),
            "history": history
        }
    
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}", exc_info=True)
        return 500, {
            "error": "HISTORY_ERROR",
            "message": f"Failed to retrieve history: {str(e)}",
            "timestamp": datetime.now()
        }


@router.get(
    "statistics",
    response={
        200: Dict[str, Any],
        500: AnalysisErrorSchema
    },
    summary="Get personal assistant request statistics",
    description="Get statistics about personal assistant requests"
)
def get_statistics(request, days: int = Query(7, ge=1, le=90)):
    """
    Get statistics about personal assistant requests.
    
    Query Parameters:
    - **days**: Period for statistics (default: 7, max: 90)
    
    Returns statistics including success rate, average processing time, etc.
    """
    try:
        stats = db.get_statistics(days=days)
        return 200, {
            "timestamp": datetime.now(),
            "statistics": stats
        }
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}", exc_info=True)
        return 500, {
            "error": "STATISTICS_ERROR",
            "message": f"Failed to retrieve statistics: {str(e)}",
            "timestamp": datetime.now()
        }


@router.get(
    "health",
    response={200: dict},
    summary="Health check",
    description="Check if the API is running"
)
def health_check(request):
    """
    Health check endpoint.
    
    Returns a simple status indicating the Personal Assistant API is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Personal Assistant API"
    }


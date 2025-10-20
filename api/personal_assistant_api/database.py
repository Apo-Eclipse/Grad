"""
Database operations for storing and retrieving analysis requests and results.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.utils import timezone
from .models import AnalysisRequest, AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisDatabase:
    """Handle database operations for analysis requests and results."""
    
    @staticmethod
    def create_request(
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = 'pending'
    ) -> AnalysisRequest:
        """Create a new analysis request record with auto-generated request_id."""
        try:
            import uuid
            request_id = f"analysis_{uuid.uuid4().hex[:16]}"
            
            request = AnalysisRequest.objects.create(
                request_id=request_id,
                query=query,
                request_data={
                    'filters': filters or {},
                    'metadata': metadata or {}
                },
                status=status
            )
            logger.info(f"Created analysis request {request_id}")
            return request
        except Exception as e:
            logger.error(f"Failed to create analysis request: {str(e)}")
            raise
    
    @staticmethod
    def update_request_status(
        request_id: str,
        status: str,
        response_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[AnalysisRequest]:
        """Update the status of an analysis request."""
        try:
            request = AnalysisRequest.objects.get(request_id=request_id)
            request.status = status
            
            if status == 'processing' and not request.started_at:
                request.started_at = timezone.now()
            
            if status == 'completed':
                request.completed_at = timezone.now()
                if request.started_at:
                    delta = request.completed_at - request.started_at
                    request.processing_time_ms = int(delta.total_seconds() * 1000)
            
            if response_data:
                request.response_data = response_data
            
            if error_message:
                request.error_message = error_message
            
            request.save()
            logger.info(f"Updated analysis request {request_id} to status {status}")
            return request
        except AnalysisRequest.DoesNotExist:
            logger.error(f"Analysis request {request_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to update analysis request: {str(e)}")
            raise
    
    @staticmethod
    def get_request(request_id: str) -> Optional[AnalysisRequest]:
        """Get an analysis request by ID."""
        try:
            return AnalysisRequest.objects.get(request_id=request_id)
        except AnalysisRequest.DoesNotExist:
            logger.warning(f"Analysis request {request_id} not found")
            return None
    
    @staticmethod
    def get_request_history(
        limit: int = 50,
        status: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[AnalysisRequest]:
        """Get analysis request history with optional filtering."""
        try:
            queryset = AnalysisRequest.objects.all()
            
            if status:
                queryset = queryset.filter(status=status)
            
            if days:
                cutoff_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=cutoff_date)
            
            return list(queryset[:limit])
        except Exception as e:
            logger.error(f"Failed to retrieve analysis history: {str(e)}")
            raise
    
    @staticmethod
    def save_analysis_result(
        request_id: str,
        steps_data: Dict[str, Any],
        database_results: Dict[str, Any],
        explanations: Dict[str, Any],
        analysis_output: Dict[str, Any],
        insights: List[str] = None,
        summary: Optional[str] = None
    ) -> Optional[AnalysisResult]:
        """Save detailed analysis results."""
        try:
            request = AnalysisRequest.objects.get(request_id=request_id)
            
            result, created = AnalysisResult.objects.update_or_create(
                analysis_request=request,
                defaults={
                    'steps_data': steps_data,
                    'database_results': database_results,
                    'explanations': explanations,
                    'analysis_output': analysis_output,
                    'insights': insights or [],
                    'summary': summary or ''
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} analysis result for {request_id}")
            return result
        except AnalysisRequest.DoesNotExist:
            logger.error(f"Analysis request {request_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to save analysis result: {str(e)}")
            raise
    
    @staticmethod
    def get_analysis_result(request_id: str) -> Optional[AnalysisResult]:
        """Get detailed analysis results for a request."""
        try:
            return AnalysisResult.objects.get(analysis_request__request_id=request_id)
        except AnalysisResult.DoesNotExist:
            logger.warning(f"Analysis result for {request_id} not found")
            return None
    
    @staticmethod
    def get_statistics(days: int = 7) -> Dict[str, Any]:
        """Get statistics about analysis requests."""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            requests = AnalysisRequest.objects.filter(created_at__gte=cutoff_date)
            
            total = requests.count()
            completed = requests.filter(status='completed').count()
            failed = requests.filter(status='failed').count()
            processing = requests.filter(status='processing').count()
            
            avg_processing_time = 0
            if completed > 0:
                total_time = sum(
                    r.processing_time_ms for r in requests.filter(status='completed')
                    if r.processing_time_ms
                ) or 0
                avg_processing_time = total_time // completed
            
            return {
                "period_days": days,
                "total_requests": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "success_rate": (completed / total * 100) if total > 0 else 0,
                "average_processing_time_ms": avg_processing_time
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            raise


def get_database() -> AnalysisDatabase:
    """Get the database handler."""
    return AnalysisDatabase()

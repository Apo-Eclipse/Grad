"""
Database models for Personal Assistant API.
"""
from django.db import models
from django.contrib.auth.models import User


class AnalysisRequest(models.Model):
    """Store analysis requests for tracking and auditing."""
    
    REQUEST_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    request_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='pending')
    
    # Request data
    query = models.TextField()
    request_data = models.JSONField(default=dict)
    
    # Response data
    response_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"AnalysisRequest {self.request_id} - {self.status}"


class AnalysisResult(models.Model):
    """Store detailed analysis results."""
    
    analysis_request = models.OneToOneField(AnalysisRequest, on_delete=models.CASCADE, related_name='result')
    
    # Analysis components
    steps_data = models.JSONField(default=dict)
    database_results = models.JSONField(default=dict)
    explanations = models.JSONField(default=dict)
    analysis_output = models.JSONField(default=dict)
    
    # Summary
    summary = models.TextField(null=True, blank=True)
    insights = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"AnalysisResult for {self.analysis_request.request_id}"

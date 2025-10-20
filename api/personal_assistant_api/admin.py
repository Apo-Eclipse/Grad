"""
Django admin configuration for Personal Assistant API models.
"""
from django.contrib import admin
from .models import AnalysisRequest, AnalysisResult


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    """Admin interface for AnalysisRequest model."""
    
    list_display = ('request_id', 'status', 'query', 'created_at', 'processing_time_ms')
    list_filter = ('status', 'created_at')
    search_fields = ('request_id', 'query')
    readonly_fields = ('request_id', 'created_at', 'started_at', 'completed_at')
    
    fieldsets = (
        ('Request Info', {
            'fields': ('request_id', 'user', 'query', 'status')
        }),
        ('Request Data', {
            'fields': ('request_data',)
        }),
        ('Response Data', {
            'fields': ('response_data', 'error_message')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'processing_time_ms')
        }),
    )


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    """Admin interface for AnalysisResult model."""
    
    list_display = ('analysis_request', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Analysis Request', {
            'fields': ('analysis_request',)
        }),
        ('Analysis Components', {
            'fields': ('steps_data', 'database_results', 'explanations', 'analysis_output')
        }),
        ('Summary', {
            'fields': ('summary', 'insights')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

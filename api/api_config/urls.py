"""
URL configuration for Personal Assistant API.
"""
from django.urls import path
from ninja import NinjaAPI
from personal_assistant_api.api import router as assistant_router

api = NinjaAPI(
    title="Personal Assistant API",
    version="1.0.0",
    description="API for interacting with the Multi-Agent Personal Assistant system", 
    docs_url="docs",
)

api.add_router("personal_assistant/", assistant_router, tags=["Personal Assistant"])

urlpatterns = [
    path("api/", api.urls),
]

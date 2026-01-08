from django.contrib import admin
from django.urls import path
from .api import api  # Import from the new file, NOT from ninja directly

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls), # standard django ninja setup
]

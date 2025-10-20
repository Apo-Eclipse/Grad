"""
WSGI config for api_config.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_config.settings')

application = get_wsgi_application()

"""
Django settings for Personal Assistant API project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    # --- 1. CORE DJANGO APPS (REQUIRED) ---
    'django.contrib.admin',          # Interface to manage your DB (highly recommended)
    'django.contrib.auth',           # <--- CRITICAL: Handles Users, Login, & Password Hashing
    'django.contrib.contenttypes',   # Tracks models (you had this one)
    'django.contrib.sessions',       # Required by Admin and Auth
    'django.contrib.messages',       # Required by Admin
    'django.contrib.staticfiles',    # Required to show CSS for the Admin panel

    # --- 2. THIRD PARTY APPS ---
    'corsheaders',                   # Handles Cross-Origin Resource Sharing (React/Vue/etc)
    'ninja',                         # Django Ninja (Don't forget this!)

    # --- 3. YOUR APPS ---
    'personal_assistant_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    
    # 1. Sessions (REQUIRED for Auth & Admin)
    'django.contrib.sessions.middleware.SessionMiddleware', 

    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # 2. Authentication (REQUIRED to populate request.user)
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 3. Messages (REQUIRED for Admin popups/errors)
    'django.contrib.messages.middleware.MessageMiddleware',

    # 4. Clickjacking Protection (Standard Security)
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 
]

# CORS Configuration for mobile app
CORS_ALLOWED_ORIGINS = [
    "http://192.168.1.3:8000",
    "http://192.168.1.3:8081",
    "http://localhost:8000",
    "http://localhost:8081",
    "http://localhost:3000",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

ROOT_URLCONF = 'api_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                
                # --- ADD THESE TWO LINES ---
                'django.contrib.auth.context_processors.auth',     # Required for Admin login
                'django.contrib.messages.context_processors.messages', # Required for Admin popups
            ],
        },
    },
]

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': os.getenv('DB_SSLMODE', 'require'),
        },
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# API Configuration
API_TITLE = 'Personal Assistant API'
API_VERSION = '1.0.0'

# Path to parent project for importing agents
PARENT_PROJECT_PATH = os.path.dirname(os.path.dirname(BASE_DIR))

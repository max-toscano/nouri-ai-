import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
    'workout_quiz',   # Workout quiz sections (goal, schedule, equipment, ...)
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME',     'nourish'),
        'USER':     os.getenv('DB_USER',     'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST':     os.getenv('DB_HOST',     'localhost'),
        'PORT':     os.getenv('DB_PORT',     '5432'),
    }
}

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_TZ = True

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(',') if o.strip()]

# Allow all origins in development when the list is empty.
# Also allow "null" so that file:// pages (opened directly in the browser)
# can reach the backend without a CORS error.
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_ALL_ORIGINS = True  # dev only — lock this down before deploying

# ── Third-party API keys ───────────────────────────────────────────────────────
# Falls back to DEMO_KEY so the USDA endpoint works out-of-the-box.
# DEMO_KEY is rate-limited to 30 req/hour. Register for a free key:
# https://fdc.nal.usda.gov/api-key-signup.html
USDA_API_KEY            = os.getenv('USDA_API_KEY', 'DEMO_KEY')
FATSECRET_CLIENT_ID     = os.getenv('FATSECRET_CLIENT_ID', '')
FATSECRET_CLIENT_SECRET = os.getenv('FATSECRET_CLIENT_SECRET', '')

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

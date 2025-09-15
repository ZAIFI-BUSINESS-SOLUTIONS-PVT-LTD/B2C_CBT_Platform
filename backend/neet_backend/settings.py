"""
Django settings for neet_backend project.
"""

import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from neomodel import config
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# Configure logging integration to capture logs at INFO level and above
logging_integration = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send records as events from error level
)

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[
        DjangoIntegration(),
        logging_integration,
    ],
    # Disable auto-enabling integrations to avoid LangChain issues
    auto_enabling_integrations=False,
    traces_sample_rate=1.0,
    send_default_pii=True
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR.parent, '.env')) # need to remove .parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,c954e41aebd0.ngrok-free.app').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'neet_app',
    'django_neomodel',
    'djangorestframework_camel_case'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Platform admin activity middleware
    'neet_app.middleware.UpdateLastSeenMiddleware',
    # Global error handling middleware
    'neet_app.exception_handler.ErrorHandlingMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'neet_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'neet_backend.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'b2c'),
        'USER': os.environ.get('DB_USER', 'inzightedb2c'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'b2c'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5433'),
    }
}

# Optional secondary database for external source (database_question)
if os.environ.get('SRC_DB_NAME'):
    DATABASES['source'] = {
        'ENGINE': os.environ.get('SRC_DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('SRC_DB_NAME'),
        'USER': os.environ.get('SRC_DB_USER', DATABASES['default']['USER']),
        'PASSWORD': os.environ.get('SRC_DB_PASSWORD', DATABASES['default']['PASSWORD']),
        'HOST': os.environ.get('SRC_DB_HOST', DATABASES['default']['HOST']),
        'PORT': os.environ.get('SRC_DB_PORT', DATABASES['default']['PORT']),
    }
NEO4J_BOLT_URL = os.environ.get('NEO4J_BOLT_URL', 'bolt://neo4j:vishal4j@localhost:7687/neo4j')
config.DATABASE_URL = NEO4J_BOLT_URL
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Heartbeat timeout used by platform admin metrics (in seconds)
HEARTBEAT_TIMEOUT_SECONDS = int(os.environ.get('HEARTBEAT_TIMEOUT_SECONDS', '90'))

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'neet_app.student_auth.StudentJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer', # Recommended for browsable API
        'rest_framework.renderers.JSONRenderer', # Keep original JSONRenderer for fallback or specific cases
        # You can add other renderers here if you use them, e.g., 'rest_framework.renderers.TemplateHTMLRenderer'
    ),
    
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'djangorestframework_camel_case.parser.CamelCaseFormParser',       # For application/x-www-form-urlencoded
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',  # For multipart/form-data (file uploads)
        'rest_framework.parsers.JSONParser', # Keep original JSONParser for fallback
        # You can add other parsers here if you use them
    ),
    
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    
    # Global exception handler for standardized error responses
    'EXCEPTION_HANDLER': 'neet_app.exception_handler.standard_exception_handler',

    # Optional: If you want to control how numbers are underscored (e.g., v2Counter -> v2_counter)
    # The default is to remove underscores before numbers (v2Counter -> v2counter)
    # 'JSON_UNDERSCOREIZE': {
    #     'no_underscore_before_number': True, 
    # },
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cbt.inzighted.com"
    
]

CORS_ALLOW_CREDENTIALS = True
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

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': os.environ.get('JWT_ROTATE_REFRESH', 'True') == 'True',
    'BLACKLIST_AFTER_ROTATION': os.environ.get('JWT_BLACKLIST_AFTER_ROTATION', 'True') == 'True',
    'UPDATE_LAST_LOGIN': os.environ.get('JWT_UPDATE_LAST_LOGIN', 'True') == 'True',
    'ALGORITHM': os.environ.get('JWT_ALGORITHM', 'HS256'),
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': os.environ.get('JWT_VERIFYING_KEY', None),
    'AUDIENCE': os.environ.get('JWT_AUDIENCE', None),
    'ISSUER': os.environ.get('JWT_ISSUER', None),
    'AUTH_HEADER_TYPES': tuple(os.environ.get('JWT_HEADER_TYPES', 'Bearer').split(',')),
    'AUTH_HEADER_NAME': os.environ.get('JWT_HEADER_NAME', 'HTTP_AUTHORIZATION'),
    'USER_ID_FIELD': os.environ.get('JWT_USER_ID_FIELD', 'id'),
    'USER_ID_CLAIM': os.environ.get('JWT_USER_ID_CLAIM', 'user_id'),
    'AUTH_TOKEN_CLASSES': tuple(os.environ.get('JWT_TOKEN_CLASSES', 'rest_framework_simplejwt.tokens.AccessToken').split(',')),
    'TOKEN_TYPE_CLAIM': os.environ.get('JWT_TOKEN_TYPE_CLAIM', 'token_type'),
    'JTI_CLAIM': os.environ.get('JWT_JTI_CLAIM', 'jti'),
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': os.environ.get('JWT_SLIDING_REFRESH_EXP_CLAIM', 'refresh_exp'),
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_SLIDING_MINUTES', '60'))),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=int(os.environ.get('JWT_SLIDING_REFRESH_DAYS', '7'))),
}

# Session configuration
SESSION_ENGINE = os.environ.get('SESSION_ENGINE', 'django.contrib.sessions.backends.db')
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', '86400'))  # 24 hours

# URL Configuration
APPEND_SLASH = os.environ.get('APPEND_SLASH', 'False') == 'True'  # Disable automatic trailing slash redirect for API consistency

# FRONTEND URL to include in password reset emails. Replace with your frontend domain in production.
FRONTEND_RESET_URL = os.environ.get('FRONTEND_RESET_URL', 'https://neet.inzighted.com/reset-password')

# Email backend configuration (placeholder/defaults)
# Update these environment variables in production with real SMTP or provider credentials.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')  # <-- UPDATE: replace with your SMTP host
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-smtp-username')  # <-- UPDATE: replace with SMTP username
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-smtp-password')  # <-- UPDATE: replace with SMTP password
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@inzighted.com')
EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'django')  # 'django' | 'smtp' | 'zeptomail'

# AI Chatbot Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Multiple Gemini API Keys for rotation (to avoid rate limits)
# You can add up to 10 API keys for automatic rotation
GEMINI_API_KEYS = [
    key.strip() for key in [
        os.environ.get('GEMINI_API_KEY_1', 'AIzaSyCiRo7SBPCG7sXcoO3SwKJ83wwS0HjMTms'),
        os.environ.get('GEMINI_API_KEY_2', 'AIzaSyBE1loGo70z8u5nFpuTTc_9R55sjxjCNhY'),
        os.environ.get('GEMINI_API_KEY_3', 'AIzaSyABTJVXvysbnjRVhPsVjLZzNktngqtzIgM'),
        os.environ.get('GEMINI_API_KEY_4', 'AIzaSyAgInt3v8pAqM_12bLWo90-32M56YvDSHY'),
        os.environ.get('GEMINI_API_KEY_5', 'AIzaSyCocQbZChhFrebz66Go1MQ5Y94imDxtT8g'),
        os.environ.get('GEMINI_API_KEY_6', 'AIzaSyAVf05frX2D1aXLmNqCindJHeO0hB_DT60'),
        os.environ.get('GEMINI_API_KEY_7', 'AIzaSyCl1_xxF-BPg7_Tnf7Sw9IDr0tO3TdL6DE'),
        os.environ.get('GEMINI_API_KEY_8', 'AIzaSyCF7VOs8OE7ADuuIvjw5Aao8L9oDN85u5Q'),
        os.environ.get('GEMINI_API_KEY_9', 'AIzaSyBp9jYYfQdUASd5nckwT9Xv6oD0_lkNikc'),
        os.environ.get('GEMINI_API_KEY_10', 'AIzaSyCqhAVgqJqqfpNKpgSJGBF2vTIKPK_77Ok'),
    ] if key.strip()
]

# Fallback to single key if no multiple keys are provided
if not GEMINI_API_KEYS and GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]

# LangChain configuration
LANGCHAIN_TRACING_V2 = os.environ.get('LANGCHAIN_TRACING_V2', 'false')
LANGCHAIN_API_KEY = os.environ.get('LANGCHAIN_API_KEY', '')

# Chatbot configuration
CHATBOT_MAX_SESSIONS = int(os.environ.get('CHATBOT_MAX_SESSIONS', '10'))
CHATBOT_MAX_MESSAGES = int(os.environ.get('CHATBOT_MAX_MESSAGES', '1000'))
CHATBOT_SESSION_TIMEOUT = int(os.environ.get('CHATBOT_SESSION_TIMEOUT', '86400'))  # 24 hours

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')


CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://neet.inzighted.com",  # for production
]
# NEET App specific settings
NEET_SETTINGS = {
    # Number of recent test sessions to check for question repetition prevention
    'RECENT_TESTS_COUNT_FOR_EXCLUSION': 1,
    
    # Adaptive question selection ratios (percentages)
    'ADAPTIVE_SELECTION_ENABLED': False,  # Feature flag to enable adaptive selection
    'ADAPTIVE_RATIO_NEW': 60,            # Percentage for new (never attempted) questions
    'ADAPTIVE_RATIO_WRONG': 30,          # Percentage for wrong/unanswered questions
    'ADAPTIVE_RATIO_CORRECT': 10,        # Percentage for correctly answered questions
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'neet_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ----------------------
# Celery / Redis settings
# ----------------------
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')
REDIS_URL = os.environ.get('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Example beat schedule (can be extended in production)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    # 'daily-insights-regenerate': {
    #     'task': 'neet_app.tasks.generate_insights_task',
    #     'schedule': crontab(hour=3, minute=0),
    #     'args': (),
    # },
}
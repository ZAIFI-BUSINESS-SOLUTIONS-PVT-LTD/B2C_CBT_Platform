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

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,c954e41aebd0.ngrok-free.app,neet.inzighted.com,testapi.inzighted.com').split(',')

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
    "https://neet.inzighted.com"
    
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
# You can add up to 10 API keys for automatic rotation. Keys MUST be provided via environment variables.
GEMINI_API_KEYS = [
    key.strip() for key in [
        os.environ.get('GEMINI_API_KEY_1'),
        os.environ.get('GEMINI_API_KEY_2'),
        os.environ.get('GEMINI_API_KEY_3'),
        os.environ.get('GEMINI_API_KEY_4'),
        os.environ.get('GEMINI_API_KEY_5'),
        os.environ.get('GEMINI_API_KEY_6'),
        os.environ.get('GEMINI_API_KEY_7'),
        os.environ.get('GEMINI_API_KEY_8'),
        os.environ.get('GEMINI_API_KEY_9'),
        os.environ.get('GEMINI_API_KEY_10'),
    ] if key and key.strip()
]

# Fallback to single key if no multiple keys are provided but a single key exists
if not GEMINI_API_KEYS and GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]

if not GEMINI_API_KEYS:
    # Warn at startup — prevents silent use of embedded or expired keys
    print("⚠️ No GEMINI_API_KEYS configured in environment; set GEMINI_API_KEY or GEMINI_API_KEY_1..10 in your .env or environment")

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
    "https://neet.inzighted.com", # for production
    "https://testapi.inzighted.com",
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
    
    # Rule-based selection engine settings
    'USE_RULE_ENGINE': True,             # Enable new 14-rule engine
    'DYNAMIC_SELECTION_MODE': False,     # Enable dynamic question selection during test
    
    # High-weightage topics that must be included (R9)
    'HIGH_WEIGHT_TOPICS': [
        'Human Physiology',
        'Organic Chemistry', 
        'Mechanics',
        'Coordination Compounds',
        'Thermodynamics',
        'Genetics',
        'Cell Biology',
        'Ecology',
        'Plant Physiology',
        'Atomic Structure'
    ],
    
    # Rule thresholds
    'ACCURACY_THRESHOLD': 60,            # R1, R5: Accuracy threshold percentage
    'TIME_THRESHOLD_SLOW': 120,          # R4: Slow response time in seconds
    'TIME_THRESHOLD_FAST': 60,           # R5: Fast response time in seconds
    'CONSECUTIVE_STREAK': 3,             # R3, R12, R13: Consecutive answer streak
    'EXCLUSION_DAYS': 15,                # R8: Days to exclude recent questions
    
    # Weak/strong topic allocation ratios (R14)
    'WEAK_TOPIC_RATIO': 70,              # Percentage for weak topics
    'STRONG_TOPIC_RATIO': 20,            # Percentage for strong topics
    'RANDOM_TOPIC_RATIO': 10,            # Percentage for random topics
    
    # Default difficulty distribution (R6)
    'DIFFICULTY_EASY_RATIO': 30,         # Percentage for easy questions
    'DIFFICULTY_MODERATE_RATIO': 40,     # Percentage for moderate questions
    'DIFFICULTY_HARD_RATIO': 30,         # Percentage for hard questions
    
    # NVT (Descriptive/Numerical Value Type) question settings
    'NVT_AUTO_EVALUATE': True,           # Enable automatic evaluation of NVT answers
    'NVT_NUMERIC_TOLERANCE': 0.01,       # Tolerance for numeric answer comparison (e.g., 3.14 vs 3.1415)
    'NVT_MAX_ANSWER_LENGTH': 2000,       # Maximum character length for text answers
    'NVT_CASE_SENSITIVE': False,         # Case-sensitive text comparison for string answers
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

# ----------------------
# Institution Tests Feature Flag
# ----------------------
FEATURE_INSTITUTION_TESTS = os.environ.get('FEATURE_INSTITUTION_TESTS', 'True') == 'True'

"""
Django settings for neet_backend project.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from neomodel import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR.parent, '.env')) # need to remove .parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

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
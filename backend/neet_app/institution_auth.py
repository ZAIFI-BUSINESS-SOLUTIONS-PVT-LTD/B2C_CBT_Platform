"""
Institution admin authentication utilities.
Provides JWT token generation and verification for institution admins.
"""

from functools import wraps
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from neet_app.models import InstitutionAdmin
import jwt
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def generate_institution_admin_tokens(institution_admin):
    """
    Generate JWT access and refresh tokens for an institution admin.
    
    Args:
        institution_admin: InstitutionAdmin instance
    
    Returns:
        dict with 'access' and 'refresh' tokens
    """
    # Use Django's SECRET_KEY for signing
    secret_key = settings.SECRET_KEY
    
    # Generate access token (1 hour expiry)
    access_payload = {
        'admin_id': institution_admin.id,
        'username': institution_admin.username,
        'institution_id': institution_admin.institution.id,
        'type': 'institution_admin',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    
    # Generate refresh token (7 days expiry)
    refresh_payload = {
        'admin_id': institution_admin.id,
        'type': 'institution_admin_refresh',
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    
    access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm='HS256')
    
    return {
        'access': access_token,
        'refresh': refresh_token
    }


def verify_institution_admin_token(token):
    """
    Verify and decode an institution admin JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        secret_key = settings.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verify token type
        if payload.get('type') != 'institution_admin':
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Institution admin token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid institution admin token: {e}")
        return None


def institution_admin_required(view_func):
    """
    Decorator to require institution admin authentication for a view.
    Expects 'Authorization: Bearer <token>' header.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'UNAUTHORIZED',
                'message': 'Missing or invalid authorization header'
            }, status=401)
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        payload = verify_institution_admin_token(token)
        if not payload:
            return JsonResponse({
                'error': 'UNAUTHORIZED',
                'message': 'Invalid or expired token'
            }, status=401)
        
        # Get institution admin
        try:
            admin = InstitutionAdmin.objects.select_related('institution').get(
                id=payload['admin_id'],
                is_active=True
            )
        except InstitutionAdmin.DoesNotExist:
            return JsonResponse({
                'error': 'UNAUTHORIZED',
                'message': 'Institution admin not found or inactive'
            }, status=401)
        
        # Add admin to request
        request.institution_admin = admin
        request.institution = admin.institution
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_institution_admin_from_request(request):
    """
    Extract institution admin from request if authenticated.
    
    Args:
        request: Django request object
    
    Returns:
        InstitutionAdmin instance or None
    """
    if hasattr(request, 'institution_admin'):
        return request.institution_admin
    
    # Try to extract from token
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    payload = verify_institution_admin_token(token)
    
    if not payload:
        return None
    
    try:
        admin = InstitutionAdmin.objects.select_related('institution').get(
            id=payload['admin_id'],
            is_active=True
        )
        return admin
    except InstitutionAdmin.DoesNotExist:
        return None

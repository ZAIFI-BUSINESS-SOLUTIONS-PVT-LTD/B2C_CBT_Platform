"""
Google OAuth authentication views for NEET Platform
Handles Google Sign-In flow and token verification
"""

import json
import requests
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import logging

from ..models import StudentProfile
from ..serializers import StudentProfileSerializer
from ..authentication import StudentUser

logger = logging.getLogger(__name__)

# Google OAuth settings
GOOGLE_CLIENT_ID = getattr(settings, 'GOOGLE_CLIENT_ID', None)
GOOGLE_CLIENT_SECRET = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)

def exchange_code_for_token(code, redirect_uri):
    """
    Exchange authorization code for ID token
    
    Args:
        code: Authorization code from Google
        redirect_uri: Redirect URI used in OAuth flow
        
    Returns:
        dict: Token response with id_token
    """
    try:
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        try:
            token_data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse Google token response as JSON: {e}, raw response: {response.text}")
            return None

        logger.info(f"Google token exchange response: {token_data}")
        if not response.ok:
            logger.error(f"Token exchange failed: {token_data}")
            return None
        return token_data
        
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None

def verify_google_token(id_token):
    """
    Verify Google ID token and return claims
    
    Args:
        id_token: Google ID token (JWT)
        
    Returns:
        dict: Token claims if valid, None if invalid
    """
    try:
        # Get Google's public keys
        response = requests.get('https://www.googleapis.com/oauth2/v3/certs', timeout=10)
        google_keys = response.json()
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(id_token)
        key_id = unverified_header.get('kid')
        
        if not key_id:
            logger.error("No key ID found in token header")
            return None
            
        # Find the right key
        public_key = None
        for key_data in google_keys.get('keys', []):
            if key_data.get('kid') == key_id:
                # For PyJWT 2.x, import RSAAlgorithm directly
                from jwt.algorithms import RSAAlgorithm
                public_key = RSAAlgorithm.from_jwk(key_data)
                break
                
        if not public_key:
            logger.error(f"Public key not found for key ID: {key_id}")
            return None
            
        # Verify and decode the token
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=['RS256'],
            audience=GOOGLE_CLIENT_ID,
            issuer=['https://accounts.google.com', 'accounts.google.com']
        )
        
        # Additional validation
        if claims.get('aud') != GOOGLE_CLIENT_ID:
            logger.error(f"Invalid audience: {claims.get('aud')}")
            return None
            
        if claims.get('iss') not in ['https://accounts.google.com', 'accounts.google.com']:
            logger.error(f"Invalid issuer: {claims.get('iss')}")
            return None
            
        # Check token expiration
        exp = claims.get('exp')
        if not exp or exp < timezone.now().timestamp():
            logger.error("Token expired")
            return None
            
        logger.info(f"Successfully verified Google token for user: {claims.get('email')}")
        return claims
        
    except ExpiredSignatureError:
        logger.error("Google token expired")
        return None
    except InvalidTokenError as e:
        logger.error(f"Invalid Google token: {e}")
        return None
    except requests.RequestException as e:
        logger.error(f"Error fetching Google keys: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Google token: {e}")
        return None

def find_or_create_student_from_google(claims):
    """
    Find existing student or create new one from Google claims
    
    Args:
        claims: Verified Google token claims
        
    Returns:
        StudentProfile: Student instance
    """
    google_sub = claims.get('sub')
    google_email = claims.get('email')
    email_verified = claims.get('email_verified', False)
    name = claims.get('name', '')
    picture = claims.get('picture')
    
    if not google_sub or not google_email:
        raise ValueError("Missing required Google claims")
    
    # Try to find existing student by Google sub
    try:
        student = StudentProfile.objects.get(google_sub=google_sub)
        logger.info(f"Found existing student by Google sub: {student.student_id}")
        
        # Update Google info if needed
        if student.google_email != google_email:
            student.google_email = google_email
        if student.email_verified != email_verified:
            student.email_verified = email_verified
        if picture and student.google_picture != picture:
            student.google_picture = picture
        student.save(update_fields=['google_email', 'email_verified', 'google_picture'])
        
        return student
        
    except StudentProfile.DoesNotExist:
        pass
    
    # Try to find existing student by email (for account linking)
    try:
        student = StudentProfile.objects.get(email__iexact=google_email)
        logger.info(f"Found existing student by email for linking: {student.student_id}")
        
        # Link Google account if email is verified
        if email_verified:
            student.link_google_account(
                google_sub=google_sub,
                google_email=google_email,
                email_verified=email_verified,
                google_picture=picture
            )
            student.save()
            logger.info(f"Linked Google account to existing student: {student.student_id}")
        else:
            raise ValueError("Cannot link unverified email account")
            
        return student
        
    except StudentProfile.DoesNotExist:
        pass
    
    # Create new student account
    logger.info(f"Creating new student account for Google user: {google_email}")
    
    # Generate student_id and other required fields
    from ..utils.student_utils import ensure_unique_student_id
    from datetime import date
    
    # Use a default birth date (can be updated later)
    default_birth_date = date(2000, 1, 1)
    
    student = StudentProfile(
        full_name=name or google_email.split('@')[0],
        email=google_email,
        date_of_birth=default_birth_date,
        google_sub=google_sub,
        google_email=google_email,
        email_verified=email_verified,
        google_picture=picture,
        auth_provider='google',
        is_verified=email_verified
    )
    
    # Generate unique student_id
    student.student_id = ensure_unique_student_id(student.full_name, student.date_of_birth)
    
    # Set unusable password for Google-only accounts
    student.set_unusable_password()
    
    student.save()
    logger.info(f"Created new student account: {student.student_id}")
    
    return student

@csrf_exempt
@authentication_classes([])
@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Authenticate user with Google ID token or authorization code
    
    POST Body (ID Token flow):
    {
        "idToken": "google_id_token_jwt"
    }
    
    POST Body (Authorization Code flow):
    {
        "code": "authorization_code",
        "state": "random_state"
    }
    
    Returns:
    {
        "refresh": "jwt_refresh_token",
        "access": "jwt_access_token", 
        "student": {...}
    }
    """
    logger.info(f"🔄 Google auth request received: {request.method}")
    logger.info(f"📋 Request headers: {dict(request.headers)}")
    logger.info(f"📋 Request content type: {request.content_type}")
    
    try:
        if not GOOGLE_CLIENT_ID:
            logger.error("❌ Google Client ID not configured")
            return Response({
                'detail': 'Google authentication not configured'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
            
        data = json.loads(request.body) if request.body else {}
        logger.info(f"📋 Request body data: {data}")
        id_token = data.get('idToken')
        auth_code = data.get('code')
        state = data.get('state')
        logger.info(f"📋 Extracted - idToken: {bool(id_token)}, code: {bool(auth_code)}, state: {state}")
        
        if id_token:
            # Direct ID token flow
            claims = verify_google_token(id_token)
            if not claims:
                return Response({
                    'detail': 'Invalid Google token'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        elif auth_code:
            # Authorization code flow
            redirect_uri = "http://localhost:5173/auth/google/callback"
            
            # Exchange code for tokens
            token_data = exchange_code_for_token(auth_code, redirect_uri)
            if not token_data or 'id_token' not in token_data:
                return Response({
                    'detail': 'Failed to exchange authorization code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify the ID token
            claims = verify_google_token(token_data['id_token'])
            if not claims:
                return Response({
                    'detail': 'Invalid Google token'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'detail': 'Google ID token or authorization code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find or create student
        try:
            student = find_or_create_student_from_google(claims)
        except ValueError as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if student is active
        if not student.is_active:
            return Response({
                'detail': 'Student account is deactivated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Update last login
        student.last_login = timezone.now()
        student.save(update_fields=['last_login'])
        
        # Create JWT tokens (same as password login)
        user = StudentUser(student)
        refresh = RefreshToken.for_user(user)
        
        # Add student data to token payload
        refresh['student_id'] = student.student_id
        refresh['email'] = student.email
        
        # Get student data and convert to camelCase
        student_data = StudentProfileSerializer(student).data
        
        # Convert snake_case keys to camelCase for consistency
        camel_case_student = {}
        for key, value in student_data.items():
            if '_' in key:
                parts = key.split('_')
                camel_key = parts[0] + ''.join(word.capitalize() for word in parts[1:])
                camel_case_student[camel_key] = value
            else:
                camel_case_student[key] = value
        
        logger.info(f"Google authentication successful for student: {student.student_id}")
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'student': camel_case_student
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response({
            'detail': 'Invalid JSON in request body'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in Google authentication: {e}")
        return Response({
            'detail': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@authentication_classes([])
@api_view(['POST'])
@permission_classes([AllowAny])  # Will implement authentication check inside
def link_google_account(request):
    """
    Link Google account to existing authenticated student
    
    Requires authentication. Links Google account to current user.
    
    POST Body:
    {
        "idToken": "google_id_token_jwt"
    }
    """
    try:
        # Check authentication
        if not hasattr(request.user, 'student_id'):
            return Response({
                'detail': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        student_id = request.user.student_id
        
        data = json.loads(request.body) if request.body else {}
        id_token = data.get('idToken')
        
        if not id_token:
            return Response({
                'detail': 'Google ID token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify Google token
        claims = verify_google_token(id_token)
        if not claims:
            return Response({
                'detail': 'Invalid Google token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get current student
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({
                'detail': 'Student not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if Google account is already linked to another user
        google_sub = claims.get('sub')
        google_email = claims.get('email')
        
        existing_google_user = StudentProfile.objects.filter(google_sub=google_sub).first()
        if existing_google_user and existing_google_user.student_id != student_id:
            return Response({
                'detail': 'Google account is already linked to another user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Link Google account
        student.link_google_account(
            google_sub=google_sub,
            google_email=google_email,
            email_verified=claims.get('email_verified', False),
            google_picture=claims.get('picture')
        )
        student.save()
        
        logger.info(f"Linked Google account to student: {student_id}")
        
        return Response({
            'detail': 'Google account linked successfully',
            'student': StudentProfileSerializer(student).data
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response({
            'detail': 'Invalid JSON in request body'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error linking Google account: {e}")
        return Response({
            'detail': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@authentication_classes([])
@api_view(['POST'])
@permission_classes([AllowAny])  # Will implement authentication check inside
def unlink_google_account(request):
    """
    Unlink Google account from authenticated student
    
    Requires authentication. Unlinks Google account from current user.
    """
    try:
        # Check authentication
        if not hasattr(request.user, 'student_id'):
            return Response({
                'detail': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        student_id = request.user.student_id
        
        # Get current student
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({
                'detail': 'Student not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if student has password set (for account recovery)
        if not student.can_login_with_password():
            return Response({
                'detail': 'Cannot unlink Google account. Please set a password first for account recovery.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Unlink Google account
        student.unlink_google_account()
        student.save()
        
        logger.info(f"Unlinked Google account from student: {student_id}")
        
        return Response({
            'detail': 'Google account unlinked successfully',
            'student': StudentProfileSerializer(student).data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error unlinking Google account: {e}")
        return Response({
            'detail': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

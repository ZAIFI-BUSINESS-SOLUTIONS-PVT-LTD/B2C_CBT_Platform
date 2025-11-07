"""
Custom authentication backend for StudentProfile model
"""
import sentry_sdk
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from .models import StudentProfile
from django.http import JsonResponse
from functools import wraps


class StudentAuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that can authenticate StudentProfile objects
    """
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        
        try:
            sentry_sdk.add_breadcrumb(
                message="Student authentication attempt",
                category="auth",
                level="info",
                data={"email": email}
            )
            
            student = StudentProfile.objects.get(email=email)
            if student.check_password(password) and student.is_active:
                sentry_sdk.add_breadcrumb(
                    message="Student authentication successful",
                    category="auth",
                    level="info",
                    data={"student_id": student.student_id, "email": email}
                )
                return student
            else:
                sentry_sdk.capture_message(
                    "Student authentication failed - invalid password or inactive account",
                    level="warning",
                    extra={"email": email, "is_active": student.is_active}
                )
        except StudentProfile.DoesNotExist:
            sentry_sdk.capture_message(
                "Student authentication failed - student not found",
                level="warning",
                extra={"email": email}
            )
            return None
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "student_authentication",
                "email": email
            })
            return None
        
        return None

    def get_user(self, user_id):
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting student user by ID",
                category="auth",
                level="info",
                data={"user_id": user_id}
            )
            
            student = StudentProfile.objects.get(student_id=user_id)
            
            sentry_sdk.add_breadcrumb(
                message="Student user retrieved successfully",
                category="auth",
                level="info",
                data={"student_id": student.student_id, "email": student.email}
            )
            
            return student
        except StudentProfile.DoesNotExist:
            sentry_sdk.capture_message(
                "Student user not found during get_user",
                level="warning",
                extra={"user_id": user_id}
            )
            return None
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_student_user",
                "user_id": user_id
            })
            return None


class StudentJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that works with StudentProfile model
    """
    def get_user(self, validated_token):
        """
        Get the user from the token, looking up by student_id
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            sentry_sdk.add_breadcrumb(
                message="JWT token validation attempt",
                category="auth",
                level="info"
            )
            
            user_id = validated_token['user_id']
            logger.info(f"JWT Authentication - user_id from token: {user_id}")
            
            sentry_sdk.add_breadcrumb(
                message="Extracting user_id from JWT token",
                category="auth",
                level="info",
                data={"user_id": user_id}
            )
            
        except KeyError:
            logger.error("Token contained no recognizable user identification")
            sentry_sdk.capture_message(
                "JWT token missing user_id",
                level="error",
                extra={"token_keys": list(validated_token.keys())}
            )
            raise InvalidToken('Token contained no recognizable user identification')

        try:
            # Look up the student by student_id (which was stored as user_id in the token)
            student = StudentProfile.objects.get(student_id=user_id)
            logger.info(f"JWT Authentication - Found student: {student.student_id} - {student.full_name}")
            
            sentry_sdk.add_breadcrumb(
                message="JWT authentication successful",
                category="auth",
                level="info",
                data={"student_id": student.student_id, "email": student.email}
            )
            
            return student
        except StudentProfile.DoesNotExist:
            logger.error(f"Student with ID {user_id} does not exist")
            sentry_sdk.capture_message(
                "JWT authentication failed - student not found",
                level="warning",
                extra={"user_id": user_id}
            )
            raise InvalidToken('User not found')
        except Exception as e:
            logger.error(f"Unexpected error during JWT authentication: {e}")
            sentry_sdk.capture_exception(e, extra={
                "action": "jwt_student_authentication",
                "user_id": user_id
            })
            raise InvalidToken('Authentication error')


def student_jwt_required(view_func):
    """
    Decorator for views that require a student JWT in the Authorization header.
    Sets `request.student` to the authenticated StudentProfile on success.
    Returns 401 JSON response on authentication failure.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        auth = StudentJWTAuthentication()
        try:
            # Extract header and raw token
            header = auth.get_header(request)
            if header is None:
                return JsonResponse({
                    'error': 'UNAUTHORIZED',
                    'message': 'Authentication credentials were not provided.'
                }, status=401)

            raw_token = auth.get_raw_token(header)
            if raw_token is None:
                return JsonResponse({
                    'error': 'UNAUTHORIZED',
                    'message': 'Invalid authentication header.'
                }, status=401)

            validated_token = auth.get_validated_token(raw_token)
            user = auth.get_user(validated_token)

            # Attach student to request to be used in views
            request.student = user
            return view_func(request, *args, **kwargs)

        except InvalidToken as e:
            sentry_sdk.capture_exception(e)
            return JsonResponse({
                'error': 'UNAUTHORIZED',
                'message': 'Invalid or expired token'
            }, status=401)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return JsonResponse({
                'error': 'SERVER_ERROR',
                'message': 'Authentication error'
            }, status=500)

    return _wrapped

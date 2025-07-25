"""
Custom authentication backend for StudentProfile model
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from .models import StudentProfile


class StudentAuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that can authenticate StudentProfile objects
    """
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        
        try:
            student = StudentProfile.objects.get(email=email)
            if student.check_password(password) and student.is_active:
                return student
        except StudentProfile.DoesNotExist:
            return None
        
        return None

    def get_user(self, user_id):
        try:
            return StudentProfile.objects.get(student_id=user_id)
        except StudentProfile.DoesNotExist:
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
            user_id = validated_token['user_id']
            logger.info(f"JWT Authentication - user_id from token: {user_id}")
        except KeyError:
            logger.error("Token contained no recognizable user identification")
            raise InvalidToken('Token contained no recognizable user identification')

        try:
            # Look up the student by student_id (which was stored as user_id in the token)
            student = StudentProfile.objects.get(student_id=user_id)
            logger.info(f"JWT Authentication - Found student: {student.student_id} - {student.full_name}")
            return student
        except StudentProfile.DoesNotExist:
            logger.error(f"Student with ID {user_id} does not exist")
            raise InvalidToken('User not found')
            return student
        except StudentProfile.DoesNotExist:
            raise InvalidToken('User not found')

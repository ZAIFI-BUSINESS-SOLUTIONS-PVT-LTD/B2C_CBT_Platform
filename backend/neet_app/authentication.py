"""
Custom JWT Authentication for NEET Practice Platform
"""
import sentry_sdk
import logging
import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers, status
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from .models import StudentProfile
from .serializers import StudentProfileSerializer
from .errors import AppError, AuthenticationError, ValidationError
from .error_codes import ErrorCodes


class StudentUser:
    """
    Custom user class for JWT authentication with StudentProfile
    """
    def __init__(self, student_profile):
        self.student_profile = student_profile
        self.id = student_profile.student_id  # Use student_id as the ID for the token
        self.pk = student_profile.student_id  
        self.username = student_profile.student_id
        self.email = student_profile.email
        self.full_name = student_profile.full_name
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        self.student_id = student_profile.student_id
        
    def __str__(self):
        return f"StudentUser: {self.student_id}"
        
    def get_username(self):
        return self.student_id


class StudentTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that works with StudentProfile model using email
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace username field with email and support username login
        self.fields['username'] = serializers.CharField(help_text="Email, Student ID, or Full Name")
        self.fields['password'] = serializers.CharField()
        # Remove default email field since we're using username for flexibility
        if 'email' in self.fields:
            del self.fields['email']

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        try:
            # Log authentication attempt
            try:
                sentry_sdk.add_breadcrumb(
                    message="JWT authentication attempt",
                    category="auth",
                    level="info",
                    data={"username": username}
                )
            except Exception:
                logging.getLogger(__name__).debug('sentry add_breadcrumb failed')
            
            if not username or not password:
                try:
                    sentry_sdk.capture_message(
                        "JWT authentication failed - missing credentials",
                        level="warning",
                        extra={"username": username, "has_password": bool(password)}
                    )
                except Exception:
                    logging.getLogger(__name__).debug('sentry capture_message failed')
                raise ValidationError('Both username and password are required.')
            
            student = None
            
            # Try to find student by email first
            try:
                student = StudentProfile.objects.get(email__iexact=username)
            except StudentProfile.DoesNotExist:
                # Try by student_id
                try:
                    student = StudentProfile.objects.get(student_id=username)
                except StudentProfile.DoesNotExist:
                    # Try by full_name (case-insensitive)
                    try:
                        student = StudentProfile.objects.get(full_name__iexact=username)
                    except StudentProfile.DoesNotExist:
                        pass
            
            if not student:
                try:
                    sentry_sdk.capture_message(
                        "JWT authentication failed - student not found",
                        level="warning",
                        extra={"username": username}
                    )
                except Exception:
                    logging.getLogger(__name__).debug('sentry capture_message failed')
                raise AuthenticationError(
                    message='Invalid credentials',
                    code=ErrorCodes.AUTH_INVALID_CREDENTIALS
                )
                
            # Check if student is active
            if not student.is_active:
                try:
                    sentry_sdk.capture_message(
                        "JWT authentication failed - student account deactivated",
                        level="warning",
                        extra={"username": username, "student_id": student.student_id}
                    )
                except Exception:
                    logging.getLogger(__name__).debug('sentry capture_message failed')
                raise AuthenticationError(
                    message='Student account is deactivated',
                    code=ErrorCodes.AUTH_FORBIDDEN
                )
            
            # Verify password
            if not student.check_password(password):
                try:
                    sentry_sdk.capture_message(
                        "JWT authentication failed - invalid password",
                        level="warning",
                        extra={"username": username, "student_id": student.student_id}
                    )
                except Exception:
                    logging.getLogger(__name__).debug('sentry capture_message failed')
                raise AuthenticationError(
                    message='Invalid credentials',
                    code=ErrorCodes.AUTH_INVALID_CREDENTIALS
                )
            
            # Log successful authentication
            try:
                sentry_sdk.add_breadcrumb(
                    message="JWT authentication successful",
                    category="auth",
                    level="info",
                    data={"student_id": student.student_id, "email": student.email}
                )
            except Exception:
                logging.getLogger(__name__).debug('sentry add_breadcrumb failed')
            
            # Update last login
            from django.utils import timezone
            student.last_login = timezone.now()
            student.save(update_fields=['last_login'])
            
            # Create or update StudentActivity so dashboard sees the login immediately
            request = self.context.get('request') if hasattr(self, 'context') else None
            try:
                from .models import StudentActivity
                now = timezone.now()
                updated = StudentActivity.objects.filter(student=student).update(
                    last_seen=now,
                    ip_address=request.META.get('REMOTE_ADDR') if request is not None else None,
                    user_agent=request.META.get('HTTP_USER_AGENT') if request is not None else None
                )
                if not updated:
                    StudentActivity.objects.create(student=student, last_seen=now,
                                                   ip_address=request.META.get('REMOTE_ADDR') if request is not None else None,
                                                   user_agent=request.META.get('HTTP_USER_AGENT') if request is not None else None)
                    logging.getLogger(__name__).info(f'Created StudentActivity for {student.student_id} on login')
            except Exception:
                # Non-fatal; don't block login on activity write failures
                logging.getLogger(__name__).exception('Failed to write StudentActivity on login')
            
            # Create a dummy user object for JWT token generation
            user = StudentUser(student)
            
            # Generate tokens with student_id as the user_id
            refresh = self.get_token(user)
            
            # Add student data to the token payload
            refresh['student_id'] = student.student_id
            refresh['email'] = student.email
            
            # Get student data and convert to camelCase
            student_data = StudentProfileSerializer(student).data
            
            # Convert snake_case keys to camelCase for consistency with frontend
            camel_case_student = {}
            for key, value in student_data.items():
                # Convert snake_case to camelCase
                if '_' in key:
                    parts = key.split('_')
                    camel_key = parts[0] + ''.join(word.capitalize() for word in parts[1:])
                    camel_case_student[camel_key] = value
                else:
                    camel_case_student[key] = value
            
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'student': camel_case_student
            }
            
        except (AuthenticationError, ValidationError):
            # Re-raise authentication and validation errors without additional Sentry capture
            raise
        except Exception as e:
            # Capture any unexpected errors in Sentry
            sentry_sdk.capture_exception(e, extra={
                "action": "jwt_authentication",
                "username": username
            })
            raise AuthenticationError(
                message='Authentication system error',
                code=ErrorCodes.SERVER_ERROR
            )
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims if needed
        return token


class StudentTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view for students
    Uses standardized error handling
    """
    serializer_class = StudentTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """Override post to use standardized error handling"""
        serializer = self.get_serializer(data=request.data)
        
        # Let the serializer validation errors be handled by our global exception handler
        serializer.is_valid(raise_exception=True)
        
        # Get the validated data (which includes student profile)
        validated_data = serializer.validated_data
        
        # Return response that will be processed by CamelCaseJSONRenderer
        return Response(validated_data)

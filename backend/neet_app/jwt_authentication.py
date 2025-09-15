"""
Custom JWT Authentication for Student Profile
"""
import sentry_sdk
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser
from .models import StudentProfile


class StudentJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that creates a proper user object from student data
    """
    
    def get_user(self, validated_token):
        """
        Get the user from the token and return a StudentUser object
        """
        try:
            # Extract student_id from token payload
            student_id = validated_token.get('student_id')
            if not student_id:
                sentry_sdk.capture_message(
                    "JWT Authentication - No student_id in token payload",
                    level="warning",
                    extra={"token_payload": validated_token}
                )
                print(f"❌ JWT Authentication - No student_id in token payload")
                return None
                
            sentry_sdk.add_breadcrumb(
                message="JWT Authentication - Looking for student",
                category="auth",
                level="info",
                data={"student_id": student_id}
            )
            print(f"🔍 JWT Authentication - Looking for student: {student_id}")
            
            # Get the actual student profile
            student = StudentProfile.objects.get(student_id=student_id)
            
            if not student.is_active:
                sentry_sdk.capture_message(
                    "JWT Authentication - Student account not active",
                    level="warning",
                    extra={"student_id": student_id}
                )
                print(f"❌ JWT Authentication - Student {student_id} is not active")
                return None
            
            sentry_sdk.add_breadcrumb(
                message="JWT Authentication successful",
                category="auth",
                level="info",
                data={"student_id": student_id, "full_name": student.full_name}
            )
            print(f"✅ JWT Authentication - Found student: {student_id} - {student.full_name}")
            
            # Create a StudentUser object that mimics Django's User model
            class StudentUser:
                def __init__(self, student_profile):
                    self.student_id = student_profile.student_id
                    self.id = student_profile.student_id
                    self.pk = student_profile.student_id
                    self.student_profile = student_profile
                    self.username = student_profile.student_id
                    self.email = student_profile.email
                    self.is_authenticated = True
                    self.is_active = student_profile.is_active
                    self.is_anonymous = False
                    self.is_staff = False
                    self.is_superuser = False
                
                def __str__(self):
                    return f"Student-{self.student_profile.student_id}"
                
                def has_perm(self, perm, obj=None):
                    return False
                
                def has_perms(self, perm_list, obj=None):
                    return False
                
                def has_module_perms(self, package_name):
                    return False
                
                def get_username(self):
                    return self.username
            
            return StudentUser(student)
            
        except StudentProfile.DoesNotExist:
            sentry_sdk.capture_message(
                "JWT Authentication - Student not found in database",
                level="warning",
                extra={"student_id": student_id}
            )
            print(f"❌ JWT Authentication - Student {student_id} not found in database")
            return None
        except (KeyError, TypeError) as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "jwt_token_validation",
                "token_payload": validated_token
            })
            print(f"❌ JWT Authentication - Token format error: {e}")
            return None

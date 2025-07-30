"""
Custom JWT Authentication for Student Profile
"""
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
            student_id = validated_token.get('student_id')
            if not student_id:
                return None
                
            # Get the actual student profile
            student = StudentProfile.objects.get(student_id=student_id)
            
            # Create a StudentUser object that mimics Django's User model
            class StudentUser:
                def __init__(self, student_profile):
                    self.student_id = student_profile.student_id
                    self.id = student_profile.student_id  # For token compatibility
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
            return None
        except (KeyError, TypeError):
            return None

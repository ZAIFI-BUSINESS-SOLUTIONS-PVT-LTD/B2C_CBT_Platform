#!/usr/bin/env python
"""
Test authentication flow for debugging JWT issues
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile
from neet_app.authentication import StudentTokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken
from neet_app.student_auth import StudentJWTAuthentication

def test_student_auth():
    print("=== Testing Student Authentication ===")
    
    # Get a student
    student = StudentProfile.objects.first()
    print(f"Student: {student}")
    print(f"Student ID: {student.student_id}")
    print(f"is_authenticated: {student.is_authenticated}")
    print(f"is_anonymous: {student.is_anonymous}")
    print(f"is_active: {student.is_active}")
    
    # Test JWT token creation
    print("\n=== Testing JWT Token Creation ===")
    
    try:
        # Simulate login request data
        login_data = {
            'email': student.email,
            'password': student.generated_password  # Use the generated password
        }
        
        print(f"Login data: {login_data}")
        
        # Create serializer and validate
        serializer = StudentTokenObtainPairSerializer(data=login_data)
        if serializer.is_valid():
            result = serializer.validated_data
            print(f"Login successful!")
            print(f"Access token: {result['access'][:50]}...")
            print(f"Full JWT response: {result}")
            if 'student' in result:
                print(f"Student data keys: {result['student'].keys()}")
                # Try both snake_case and camelCase
                student_id = result['student'].get('studentId') or result['student'].get('student_id')
                print(f"Student ID: {student_id}")
            
            # Test token validation
            print("\n=== Testing Token Validation ===")
            auth = StudentJWTAuthentication()
            
            # Parse the token
            from rest_framework_simplejwt.tokens import UntypedToken
            token = UntypedToken(result['access'])
            print(f"Token payload: {token.payload}")
            
            # Get user from token
            user = auth.get_user(token)
            print(f"User from token: {user}")
            print(f"User type: {type(user)}")
            print(f"User student_id: {user.student_id}")
            print(f"User is_authenticated: {user.is_authenticated}")
            print(f"User is_anonymous: {user.is_anonymous}")
            
        else:
            print(f"Login validation failed: {serializer.errors}")
            
    except Exception as e:
        print(f"Error during JWT test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_student_auth()

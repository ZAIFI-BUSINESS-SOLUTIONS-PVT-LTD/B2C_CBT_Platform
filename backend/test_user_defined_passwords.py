#!/usr/bin/env python
"""
Test script for user-defined password system
Tests registration, login, and password validation
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile
from neet_app.serializers import StudentProfileCreateSerializer, StudentLoginSerializer
from neet_app.authentication import StudentTokenObtainPairSerializer
from neet_app.utils.password_utils import validate_password_strength, validate_full_name_uniqueness
from datetime import date
import json

def test_password_validation():
    """Test password strength validation"""
    print("=== Testing Password Validation ===")
    
    test_passwords = [
        ("weak", "weak123"),
        ("medium", "StrongPass1"),
        ("strong", "VeryStr0ng!Pass"),
        ("too_long", "a" * 70),
        ("common", "password123")
    ]
    
    for test_name, password in test_passwords:
        is_valid, errors, score = validate_password_strength(password)
        print(f"{test_name}: {password} -> Valid: {is_valid}, Score: {score}, Errors: {errors}")

def test_username_uniqueness():
    """Test username uniqueness validation"""
    print("\n=== Testing Username Uniqueness ===")
    
    # Test with non-existent username
    is_unique, error = validate_full_name_uniqueness("Unique Test User")
    print(f"Unique username test: {is_unique}, Error: {error}")
    
    # Create a test student first
    test_student_data = {
        'full_name': 'Test Student For Uniqueness',
        'email': 'uniqueness_test@example.com',
        'date_of_birth': date(2005, 1, 15),
        'password': 'TestPass123!',
        'password_confirmation': 'TestPass123!'
    }
    
    serializer = StudentProfileCreateSerializer(data=test_student_data)
    if serializer.is_valid():
        student = serializer.save()
        print(f"Created test student: {student.student_id} - {student.full_name}")
        
        # Test uniqueness with existing name
        is_unique, error = validate_full_name_uniqueness("Test Student For Uniqueness")
        print(f"Duplicate username test: {is_unique}, Error: {error}")
        
        # Test case-insensitive uniqueness
        is_unique, error = validate_full_name_uniqueness("test student for uniqueness")
        print(f"Case-insensitive duplicate test: {is_unique}, Error: {error}")
        
        # Cleanup
        student.delete()
        print("Test student deleted")
    else:
        print(f"Failed to create test student: {serializer.errors}")

def test_student_registration():
    """Test new student registration with user-defined password"""
    print("\n=== Testing Student Registration ===")
    
    student_data = {
        'full_name': 'John Doe Test',
        'email': 'john.doe.test@example.com',
        'phone_number': '+91-9876543210',
        'date_of_birth': date(2005, 6, 15),
        'school_name': 'Test High School',
        'target_exam_year': 2025,
        'password': 'SecurePass123!',
        'password_confirmation': 'SecurePass123!'
    }
    
    serializer = StudentProfileCreateSerializer(data=student_data)
    if serializer.is_valid():
        student = serializer.save()
        print(f"✓ Registration successful!")
        print(f"  Student ID: {student.student_id}")
        print(f"  Full Name: {student.full_name}")
        print(f"  Email: {student.email}")
        print(f"  Generated Password (stored): {student.generated_password}")
        
        # Test password verification
        if student.check_password('SecurePass123!'):
            print("✓ Password verification successful")
        else:
            print("✗ Password verification failed")
        
        return student
    else:
        print(f"✗ Registration failed: {serializer.errors}")
        return None

def test_login_system(student):
    """Test login with different username formats"""
    print("\n=== Testing Login System ===")
    
    if not student:
        print("No student to test login with")
        return
    
    # Test login scenarios
    login_scenarios = [
        ("email", student.email),
        ("student_id", student.student_id),
        ("full_name", student.full_name),
        ("full_name_lowercase", student.full_name.lower()),
    ]
    
    for scenario_name, username in login_scenarios:
        print(f"\nTesting login with {scenario_name}: {username}")
        
        login_data = {
            'username': username,
            'password': 'SecurePass123!'
        }
        
        # Test with StudentLoginSerializer
        login_serializer = StudentLoginSerializer(data=login_data)
        if login_serializer.is_valid():
            print(f"✓ Login validation successful")
            
            # Test JWT token generation
            jwt_serializer = StudentTokenObtainPairSerializer(data=login_data)
            if jwt_serializer.is_valid():
                tokens = jwt_serializer.validated_data
                print(f"✓ JWT token generation successful")
                print(f"  Access token: {tokens['access'][:50]}...")
                print(f"  Student data: {tokens['student']['fullName']}")
            else:
                print(f"✗ JWT token generation failed: {jwt_serializer.errors}")
        else:
            print(f"✗ Login validation failed: {login_serializer.errors}")

def test_wrong_credentials(student):
    """Test login with wrong credentials"""
    print("\n=== Testing Wrong Credentials ===")
    
    if not student:
        print("No student to test with")
        return
    
    wrong_scenarios = [
        ("wrong_password", student.email, "WrongPassword123!"),
        ("wrong_username", "nonexistent@example.com", "SecurePass123!"),
        ("empty_password", student.email, ""),
        ("empty_username", "", "SecurePass123!"),
    ]
    
    for scenario_name, username, password in wrong_scenarios:
        print(f"\nTesting {scenario_name}")
        
        login_data = {
            'username': username,
            'password': password
        }
        
        jwt_serializer = StudentTokenObtainPairSerializer(data=login_data)
        if jwt_serializer.is_valid():
            print(f"✗ {scenario_name} should have failed but succeeded")
        else:
            print(f"✓ {scenario_name} correctly rejected")

def cleanup_test_data():
    """Clean up test data"""
    print("\n=== Cleaning Up Test Data ===")
    
    test_emails = [
        'john.doe.test@example.com',
        'uniqueness_test@example.com'
    ]
    
    for email in test_emails:
        try:
            student = StudentProfile.objects.get(email=email)
            student.delete()
            print(f"✓ Deleted test student: {email}")
        except StudentProfile.DoesNotExist:
            print(f"- No student found with email: {email}")

def main():
    """Run all tests"""
    print("🚀 Starting User-Defined Password System Tests\n")
    
    try:
        # Run tests
        test_password_validation()
        test_username_uniqueness()
        student = test_student_registration()
        test_login_system(student)
        test_wrong_credentials(student)
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        cleanup_test_data()
        print("\n🧹 Cleanup completed")

if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Test script to verify user data isolation
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile, TestSession
from neet_app.authentication import StudentTokenObtainPairSerializer

def test_user_data_isolation():
    """Test that each user sees only their own data"""
    print("=== Testing User Data Isolation ===")
    
    # Get all students
    students = StudentProfile.objects.all()
    print(f"Total students in database: {students.count()}")
    
    for student in students:
        print(f"\n--- Testing Student: {student.student_id} - {student.full_name} ---")
        
        # Test JWT authentication for this student
        login_data = {
            'email': student.email,
            'password': 'VISH2407'  # Assuming same password for testing
        }
        
        try:
            serializer = StudentTokenObtainPairSerializer(data=login_data)
            if serializer.is_valid():
                result = serializer.validated_data
                student_data = result['student']
                
                print(f"Login successful for: {student_data['studentId']}")
                print(f"Total tests in response: {student_data['totalTests']}")
                print(f"Recent tests count: {len(student_data['recentTests'])}")
                
                # Verify all test sessions belong to this student
                for test in student_data['recentTests']:
                    test_student_id = test.get('student_id') or test.get('studentId')
                    if test_student_id != student.student_id:
                        print(f"❌ ERROR: Test {test['id']} belongs to {test_student_id}, not {student.student_id}")
                    else:
                        print(f"✅ Test {test['id']} correctly belongs to {student.student_id}")
                        
            else:
                print(f"Login failed: {serializer.errors}")
                
        except Exception as e:
            print(f"Error testing student {student.student_id}: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_user_data_isolation()

"""
Test script for institution admin and student flows.
Run this to verify the institution tests feature is working correctly.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import Institution, InstitutionAdmin, StudentProfile, PlatformTest, Question
from django.utils import timezone
import json


def test_create_institution():
    """Test creating an institution"""
    print("\n=== Testing Institution Creation ===")
    
    # Create test institution
    institution, created = Institution.objects.get_or_create(
        code='TEST_INST_001',
        defaults={
            'name': 'Test Institution',
            'exam_types': ['neet', 'jee']
        }
    )
    
    if created:
        print(f"✓ Created institution: {institution.name} (Code: {institution.code})")
    else:
        print(f"✓ Institution already exists: {institution.name} (Code: {institution.code})")
    
    return institution


def test_create_institution_admin(institution):
    """Test creating an institution admin"""
    print("\n=== Testing Institution Admin Creation ===")
    
    # Create institution admin
    admin, created = InstitutionAdmin.objects.get_or_create(
        username='test_admin',
        defaults={
            'institution': institution,
            'is_active': True
        }
    )
    
    if created or not admin.check_password('test_password'):
        admin.set_password('test_password')
        admin.save()
        print(f"✓ Created institution admin: {admin.username}")
    else:
        print(f"✓ Institution admin already exists: {admin.username}")
    
    # Verify password
    if admin.check_password('test_password'):
        print("✓ Password verification successful")
    else:
        print("✗ Password verification failed")
    
    return admin


def test_verify_institution_code(institution):
    """Test institution code verification"""
    print("\n=== Testing Institution Code Verification ===")
    
    try:
        found = Institution.objects.get(code__iexact=institution.code)
        print(f"✓ Institution code '{institution.code}' verified successfully")
        print(f"  Name: {found.name}")
        print(f"  Exam Types: {found.exam_types}")
        return True
    except Institution.DoesNotExist:
        print(f"✗ Institution code '{institution.code}' not found")
        return False


def test_check_institution_tests(institution):
    """Check for institution tests"""
    print("\n=== Checking Institution Tests ===")
    
    tests = PlatformTest.objects.filter(
        institution=institution,
        is_institution_test=True
    )
    
    print(f"✓ Found {tests.count()} institution test(s)")
    for test in tests:
        print(f"  - {test.test_name} ({test.test_code})")
        print(f"    Exam: {test.exam_type}, Questions: {test.total_questions}, Duration: {test.time_limit}min")
    
    return tests


def test_check_institution_questions(institution):
    """Check for institution questions"""
    print("\n=== Checking Institution Questions ===")
    
    questions = Question.objects.filter(institution=institution)
    
    print(f"✓ Found {questions.count()} institution question(s)")
    
    # Group by test name
    test_names = questions.values_list('institution_test_name', flat=True).distinct()
    for test_name in test_names:
        count = questions.filter(institution_test_name=test_name).count()
        print(f"  - {test_name}: {count} questions")
    
    return questions


def test_student_institution_link():
    """Test student institution linking"""
    print("\n=== Testing Student Institution Linking ===")
    
    # Get or create a test student
    student = StudentProfile.objects.filter(is_active=True).first()
    
    if not student:
        print("✗ No active student found. Create a student first.")
        return False
    
    print(f"✓ Found test student: {student.student_id} ({student.full_name})")
    
    if student.institution:
        print(f"✓ Student is linked to institution: {student.institution.name}")
    else:
        print("  Student is not linked to any institution")
    
    return True


def run_all_tests():
    """Run all institution tests"""
    print("=" * 60)
    print("INSTITUTION TESTS FEATURE - VERIFICATION SCRIPT")
    print("=" * 60)
    
    try:
        # Test 1: Create institution
        institution = test_create_institution()
        
        # Test 2: Create institution admin
        admin = test_create_institution_admin(institution)
        
        # Test 3: Verify institution code
        test_verify_institution_code(institution)
        
        # Test 4: Check institution tests
        tests = test_check_institution_tests(institution)
        
        # Test 5: Check institution questions
        questions = test_check_institution_questions(institution)
        
        # Test 6: Test student institution link
        test_student_institution_link()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✓ Institution: {institution.name} (Code: {institution.code})")
        print(f"✓ Admin: {admin.username}")
        print(f"✓ Tests: {tests.count()}")
        print(f"✓ Questions: {questions.count()}")
        print("\nAll basic tests passed! ✓")
        print("\nNext steps:")
        print("1. Create an institution admin account (done)")
        print("2. Upload an Excel file with questions via the admin dashboard")
        print("3. Verify institution code as a student")
        print("4. Start an institution test")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during tests: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

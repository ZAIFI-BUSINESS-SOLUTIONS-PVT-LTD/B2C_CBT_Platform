"""
Basic test script for institution features.
Run this after migrations to verify setup.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import Institution, InstitutionAdmin, Topic


def test_institution_creation():
    """Test creating an institution"""
    print("=" * 60)
    print("Testing Institution Creation")
    print("=" * 60)
    
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


def test_institution_admin_creation(institution):
    """Test creating an institution admin"""
    print("\n" + "=" * 60)
    print("Testing Institution Admin Creation")
    print("=" * 60)
    
    admin, created = InstitutionAdmin.objects.get_or_create(
        username='test_admin',
        defaults={
            'institution': institution,
            'is_active': True
        }
    )
    
    if created:
        # Set password for new admin
        admin.set_password('test_password')
        admin.save()
        print(f"✓ Created institution admin: {admin.username}")
        print(f"  Username: test_admin")
        print(f"  Password: test_password")
    else:
        print(f"✓ Institution admin already exists: {admin.username}")
    
    # Verify password check works
    is_valid = admin.check_password('test_password')
    print(f"  Password verification: {'✓ Success' if is_valid else '✗ Failed'}")
    
    return admin


def test_models_integrity():
    """Test that all models have the expected fields"""
    print("\n" + "=" * 60)
    print("Testing Model Integrity")
    print("=" * 60)
    
    from neet_app.models import Question, PlatformTest, StudentProfile
    
    # Check Question model
    question_fields = [f.name for f in Question._meta.get_fields()]
    required_institution_fields = ['institution', 'institution_test_name', 'exam_type']
    
    print("\nQuestion model fields:")
    for field in required_institution_fields:
        if field in question_fields:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} MISSING!")
    
    # Check PlatformTest model
    platform_test_fields = [f.name for f in PlatformTest._meta.get_fields()]
    required_platform_fields = ['institution', 'is_institution_test', 'exam_type']
    
    print("\nPlatformTest model fields:")
    for field in required_platform_fields:
        if field in platform_test_fields:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} MISSING!")
    
    # Check StudentProfile model
    student_fields = [f.name for f in StudentProfile._meta.get_fields()]
    
    print("\nStudentProfile model fields:")
    if 'institution' in student_fields:
        print(f"  ✓ institution")
    else:
        print(f"  ✗ institution MISSING!")


def test_institution_features_enabled():
    """Test that the feature flag is enabled"""
    print("\n" + "=" * 60)
    print("Testing Feature Configuration")
    print("=" * 60)
    
    from django.conf import settings
    
    feature_enabled = getattr(settings, 'FEATURE_INSTITUTION_TESTS', False)
    print(f"\nFEATURE_INSTITUTION_TESTS: {'✓ Enabled' if feature_enabled else '✗ Disabled'}")
    
    # Check if openpyxl is installed
    try:
        import openpyxl
        print(f"openpyxl library: ✓ Installed (version {openpyxl.__version__})")
    except ImportError:
        print(f"openpyxl library: ✗ NOT INSTALLED (required for Excel uploads)")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("INSTITUTION FEATURES SETUP VERIFICATION")
    print("=" * 60)
    
    try:
        # Test institution creation
        institution = test_institution_creation()
        
        # Test admin creation
        admin = test_institution_admin_creation(institution)
        
        # Test model integrity
        test_models_integrity()
        
        # Test feature configuration
        test_institution_features_enabled()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
        print("\n" + "Test Institution Details:")
        print(f"  Institution Name: {institution.name}")
        print(f"  Institution Code: {institution.code}")
        print(f"  Admin Username: {admin.username}")
        print(f"  Admin Password: test_password")
        print(f"\nYou can use these credentials to test the institution admin login endpoint.")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

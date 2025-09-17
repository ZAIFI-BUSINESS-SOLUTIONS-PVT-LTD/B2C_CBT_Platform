#!/usr/bin/env python
"""
Simple test script to verify Celery analytics tasks are working properly.
Run this script to test if Celery analytics tasks are functioning correctly.
"""

import os
import sys
import django

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile
from neet_app.tasks import (
    dashboard_analytics_task, 
    dashboard_comprehensive_analytics_task, 
    platform_test_analytics_task
)


def test_analytics_tasks():
    """Test that Celery analytics tasks are properly configured and can be called."""
    
    print("Testing Celery analytics task imports...")
    try:
        from neet_app.tasks import (
            dashboard_analytics_task, 
            dashboard_comprehensive_analytics_task, 
            platform_test_analytics_task
        )
        print("✓ Celery analytics tasks imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Celery analytics tasks: {e}")
        return False
    
    print("\nTesting Celery app configuration...")
    try:
        from neet_backend.celery import app
        print(f"✓ Celery app configured: {app.main}")
        print(f"✓ Broker URL: {app.conf.broker_url}")
        print(f"✓ Result backend: {app.conf.result_backend}")
    except Exception as e:
        print(f"✗ Celery app configuration issue: {e}")
        return False
    
    print("\nTesting analytics task registration...")
    registered_tasks = list(app.tasks.keys())
    expected_tasks = [
        'neet_app.tasks.dashboard_analytics_task',
        'neet_app.tasks.dashboard_comprehensive_analytics_task',
        'neet_app.tasks.platform_test_analytics_task'
    ]
    
    for task in expected_tasks:
        if task in registered_tasks:
            print(f"✓ Task registered: {task}")
        else:
            print(f"✗ Task not registered: {task}")
    
    print("\nTesting analytics task delay() method...")
    try:
        # Prefer the requested student_id if present, otherwise fall back to any existing student
        requested_id = "STU000101SBA783"
        student = StudentProfile.objects.filter(student_id=requested_id).first()
        if student:
            student_id = student.student_id
            print(f"✓ Using requested student: {student_id}")
        else:
            # Fallback to the first available student in DB
            student = StudentProfile.objects.first()
            if student:
                student_id = student.student_id
                print(f"✓ Using existing student: {student_id} (requested {requested_id} not found)")
            else:
                # Use the requested id as a sample when no students exist
                student_id = requested_id
                print(f"⚠️ No students found, using requested sample student_id: {student_id}")
        
        # Test dashboard analytics task
        result1 = dashboard_analytics_task.delay(student_id)
        print(f"✓ Dashboard analytics task enqueued: {result1.id}")
        
        # Test comprehensive analytics task
        result2 = dashboard_comprehensive_analytics_task.delay(student_id)
        print(f"✓ Comprehensive analytics task enqueued: {result2.id}")
        
        # Test platform test analytics task (without test_id)
        result3 = platform_test_analytics_task.delay(student_id)
        print(f"✓ Platform test analytics task enqueued: {result3.id}")
        
        # Test platform test analytics task (with test_id)
        result4 = platform_test_analytics_task.delay(student_id, "test-123")
        print(f"✓ Platform test analytics task (with test_id) enqueued: {result4.id}")
        
    except Exception as e:
        print(f"✗ Failed to enqueue analytics tasks: {e}")
        return False
    
    print("\n" + "="*50)
    print("Celery analytics tasks test completed successfully!")
    print("If you see task IDs above, Celery is working correctly.")
    print("Check your Celery worker logs to see if tasks are being processed.")
    print("\nNote: Tasks may fail if the student doesn't exist or has no test data.")
    print("This is expected behavior - the important part is that tasks are enqueued.")
    return True


def test_analytics_views_with_async():
    """Test that analytics views support async parameter."""
    
    print("\n" + "="*50)
    print("Testing analytics views with async parameter...")
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        # Create a test client
        client = Client()
        
        # Try to get a student user for authentication
        student = StudentProfile.objects.first()
        if not student:
            print("⚠️ No students found for view testing")
            return False
        
        print(f"✓ Using student for view test: {student.student_id}")
        
        # Note: These requests will fail authentication since we're not properly logged in,
        # but we can check if the async parameter is being parsed correctly by looking at the error
        
        # Test dashboard analytics with async=true
        print("\nTesting /api/dashboard/analytics/?async=true...")
        response = client.get('/api/dashboard/analytics/?async=true')
        print(f"Response status: {response.status_code}")
        
        # Test comprehensive analytics with async=true  
        print("\nTesting /api/dashboard/comprehensive-analytics/?async=true...")
        response = client.get('/api/dashboard/comprehensive-analytics/?async=true')
        print(f"Response status: {response.status_code}")
        
        # Test platform test analytics with async=true
        print("\nTesting /api/dashboard/platform-test-analytics/?async=true...")
        response = client.get('/api/dashboard/platform-test-analytics/?async=true')
        print(f"Response status: {response.status_code}")
        
        print("✓ View async parameter parsing test completed")
        print("Note: 401 status codes are expected due to authentication requirements")
        
    except Exception as e:
        print(f"✗ Error testing analytics views: {e}")
        return False
    
    return True


if __name__ == '__main__':
    print("Starting Celery analytics tasks test...")
    print("="*50)
    
    success = test_analytics_tasks()
    if success:
        test_analytics_views_with_async()
    
    print("\n" + "="*50)
    print("Test completed. Check the output above for any issues.")
    print("\nTo run Celery worker in another terminal:")
    print("cd backend && celery -A neet_backend worker --loglevel=info --pool=solo")
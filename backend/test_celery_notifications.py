#!/usr/bin/env python
"""
Simple test script to verify Celery tasks are being triggered for notifications.
Run this script to test if Celery tasks are working properly.
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
from neet_app.notifications import dispatch_welcome_email, dispatch_test_result_email
from neet_app.tasks import send_welcome_email_task, send_test_result_email_task


def test_celery_tasks():
    """Test that Celery tasks are properly configured and can be called."""
    
    print("Testing Celery task imports...")
    try:
        from neet_app.tasks import send_welcome_email_task, send_test_result_email_task
        print("✓ Celery tasks imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Celery tasks: {e}")
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
    
    print("\nTesting task registration...")
    registered_tasks = list(app.tasks.keys())
    expected_tasks = [
        'neet_app.tasks.send_welcome_email_task',
        'neet_app.tasks.send_test_result_email_task',
        'neet_app.tasks.send_inactivity_reminder_task'
    ]
    
    for task in expected_tasks:
        if task in registered_tasks:
            print(f"✓ Task registered: {task}")
        else:
            print(f"✗ Task not registered: {task}")
    
    print("\nTesting task delay() method...")
    try:
        # Test welcome email task (dry run)
        result = send_welcome_email_task.delay("STU000101SBA783")  # Using a sample student_id format
        print(f"✓ Welcome email task enqueued: {result.id}")
        
        # Test test result email task (dry run)
        test_results = {
            'session_id': 'test-123',
            'total_questions': 10,
            'correct_answers': 8,
            'incorrect_answers': 2,
            'unanswered_questions': 0,
            'time_taken': 300,
            'score_percentage': 80.0
        }
        result = send_test_result_email_task.delay("STU000101SBA783", test_results)
        print(f"✓ Test result email task enqueued: {result.id}")
        
    except Exception as e:
        print(f"✗ Failed to enqueue tasks: {e}")
        return False
    
    print("\n" + "="*50)
    print("Celery tasks test completed successfully!")
    print("If you see task IDs above, Celery is working correctly.")
    print("Check your Celery worker logs to see if tasks are being processed.")
    return True


def test_notification_functions():
    """Test that notification functions are calling Celery tasks."""
    
    print("\nTesting notification function integration...")
    
    # Try to get a real user or create a mock one
    try:
        user = StudentProfile.objects.first()
        if not user:
            print("No users found in database. Creating a test user...")
            # Generate a test student_id in the expected format
            from datetime import datetime
            now = datetime.now()
            test_student_id = f"STU{now.strftime('%y%d%m')}001"
            
            user = StudentProfile.objects.create(
                student_id=test_student_id,
                email='test@example.com',
                full_name='Test User',
                date_of_birth='2000-01-01',
                password_hash='test_hash',
                is_active=True
            )
            print(f"✓ Created test user: {user.email} with student_id: {user.student_id}")
    except Exception as e:
        print(f"✗ Failed to get/create test user: {e}")
        return False
    
    # Test welcome email dispatch
    try:
        result = dispatch_welcome_email(user)
        if result:
            print("✓ Welcome email dispatch successful")
        else:
            print("✗ Welcome email dispatch failed")
    except Exception as e:
        print(f"✗ Welcome email dispatch error: {e}")
    
    # Test test result email dispatch
    try:
        test_results = {
            'session_id': 'test-456',
            'total_questions': 15,
            'correct_answers': 12,
            'incorrect_answers': 3,
            'unanswered_questions': 0,
            'time_taken': 450,
            'score_percentage': 80.0
        }
        result = dispatch_test_result_email(user, test_results)
        if result:
            print("✓ Test result email dispatch successful")
        else:
            print("✗ Test result email dispatch failed")
    except Exception as e:
        print(f"✗ Test result email dispatch error: {e}")
    
    return True


if __name__ == '__main__':
    print("Starting Celery notifications test...")
    print("="*50)
    
    success = test_celery_tasks()
    if success:
        test_notification_functions()
    
    print("\n" + "="*50)
    print("Test completed. Check the output above for any issues.")
    print("\nTo run Celery worker in another terminal:")
    print("cd backend && celery -A neet_backend worker --loglevel=info")
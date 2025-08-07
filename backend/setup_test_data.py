#!/usr/bin/env python3
"""
Setup test data for chatbot testing
"""

import os
import django
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile, ChatSession


def setup_test_data():
    """Create test student and chat sessions"""
    try:
        # Create test student with all required fields
        student, created = StudentProfile.objects.get_or_create(
            student_id='12345',
            defaults={
                'full_name': 'Test Student',
                'email': 'test@example.com',
                'date_of_birth': date(2005, 1, 15),  # 18 years old NEET aspirant
                'target_exam_year': 2025,
                'is_active': True,
                'is_verified': False,
            }
        )
        
        status = "Created" if created else "Found"
        print(f'✅ Student {student.student_id}: {status}')
        print(f'   Name: {student.full_name}')
        print(f'   Email: {student.email}')
        print(f'   DOB: {student.date_of_birth}')
        print(f'   Target Year: {student.target_exam_year}')
        
        # Create test chat sessions
        session_count = 0
        for i in range(1, 6):
            session_id = f'test_session_{i}'
            session, session_created = ChatSession.objects.get_or_create(
                chat_session_id=session_id,
                defaults={'student_id': student.student_id}
            )
            
            if session_created:
                session_count += 1
            
            session_status = "Created" if session_created else "Found"
            print(f'✅ Chat Session {session_id}: {session_status}')
        
        print(f'\n🎯 Test setup complete!')
        print(f'   - Test Student: {student.student_id}')
        print(f'   - Chat Sessions: 5 sessions ready')
        print(f'   - New sessions created: {session_count}')
        return True
        
    except Exception as e:
        print(f'❌ Test setup failed: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    setup_test_data()

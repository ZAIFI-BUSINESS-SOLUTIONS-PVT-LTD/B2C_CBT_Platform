#!/usr/bin/env python
"""
Test script to verify the question exclusion logic is working correctly.
This script tests the new feature that prevents questions from appearing 
in a student's new test if they were used in their last 3 tests.
"""

import os
import sys
import django

# Add the parent directory to Python path to import Django modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from django.utils import timezone
from neet_app.models import StudentProfile, TestSession, TestAnswer, Question, Topic
from neet_app.views.utils import generate_questions_for_topics

def create_test_student():
    """Create a test student for our experiments"""
    student = StudentProfile.objects.create(
        full_name="Test Student - Exclusion Logic",
        email=f"test_exclusion_{timezone.now().timestamp()}@example.com",
        phone_number="+91-9999999999",
        date_of_birth="2005-01-15",
        school_name="Test School",
        target_exam_year=2025
    )
    print(f"Created test student: {student.student_id}")
    return student

def create_test_sessions_with_questions(student, num_sessions=3):
    """Create test sessions and assign questions to them"""
    sessions = []
    
    # Get some topics for testing
    topics = Topic.objects.all()[:10]  # Get first 10 topics
    if not topics.exists():
        print("No topics found in database. Please add some topics first.")
        return []
    
    topic_ids = [str(topic.id) for topic in topics]
    
    for i in range(num_sessions):
        # Create test session
        session = TestSession.objects.create(
            student_id=student.student_id,
            selected_topics=topic_ids,
            time_limit=60,
            question_count=5,
            start_time=timezone.now(),
            total_questions=5,
            is_completed=True  # Mark as completed
        )
        
        # Get questions for this session
        questions = generate_questions_for_topics(topic_ids, 5)
        
        # Create TestAnswer records to track which questions were used
        for question in questions:
            TestAnswer.objects.create(
                session=session,
                question=question,
                selected_answer='A',  # Dummy answer
                is_correct=True,
                answered_at=timezone.now()
            )
        
        sessions.append(session)
        question_ids = [q.id for q in questions]
        print(f"Session {i+1}: {session.id} - Questions: {question_ids}")
    
    return sessions

def test_exclusion_logic(student):
    """Test that questions from recent tests are excluded"""
    print("\n=== Testing Question Exclusion Logic ===")
    
    # Get recent question IDs
    recent_question_ids = TestSession.get_recent_question_ids_for_student(student.student_id)
    print(f"Recent question IDs to exclude: {recent_question_ids}")
    
    # Get some topics
    topics = Topic.objects.all()[:10]
    topic_ids = [str(topic.id) for topic in topics]
    
    # Generate questions with exclusion
    new_questions = generate_questions_for_topics(
        topic_ids, 
        question_count=5, 
        exclude_question_ids=recent_question_ids
    )
    
    new_question_ids = set(q.id for q in new_questions)
    print(f"New test question IDs: {new_question_ids}")
    
    # Check for overlap
    overlap = new_question_ids.intersection(recent_question_ids)
    if overlap:
        print(f"❌ FAILED: Found overlapping questions: {overlap}")
        print("Questions from recent tests appeared in new test!")
    else:
        print("✅ SUCCESS: No questions from recent tests appeared in new test!")
    
    return len(overlap) == 0

def main():
    """Main test function"""
    print("Testing Question Exclusion Logic for NEET Platform")
    print("=" * 50)
    
    try:
        # Create test student
        student = create_test_student()
        
        # Create 3 previous test sessions with questions
        print(f"\nCreating 3 previous test sessions for student {student.student_id}...")
        sessions = create_test_sessions_with_questions(student, 3)
        
        if not sessions:
            print("Failed to create test sessions. Exiting.")
            return
        
        # Test the exclusion logic
        success = test_exclusion_logic(student)
        
        print(f"\n=== Test Results ===")
        if success:
            print("✅ Question exclusion logic is working correctly!")
        else:
            print("❌ Question exclusion logic has issues!")
        
        # Clean up (optional)
        print(f"\nCleaning up test data...")
        for session in sessions:
            TestAnswer.objects.filter(session=session).delete()
            session.delete()
        student.delete()
        print("Test data cleaned up.")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

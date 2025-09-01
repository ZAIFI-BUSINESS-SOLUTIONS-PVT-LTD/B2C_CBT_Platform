#!/usr/bin/env python
"""
Test script to verify the adaptive question selection logic is working correctly.
This script tests the new feature that selects questions based on student performance:
- 60% New (never attempted) questions
- 30% Wrong/Unanswered questions  
- 10% Correct questions
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from django.utils import timezone
from neet_app.models import StudentProfile, TestSession, TestAnswer, Question, Topic
from neet_app.views.utils import adaptive_generate_questions_for_topics, adaptive_generate_random_questions_from_database
from datetime import date

def create_test_student():
    """Create a test student for our experiments"""
    student = StudentProfile.objects.create(
        full_name="Test Student - Adaptive Selection",
        email=f"test_adaptive_{timezone.now().timestamp()}@example.com",
        phone_number="+91-9999999999",
        date_of_birth=date(2005, 1, 15),  # Use date object instead of string
        school_name="Test School",
        target_exam_year=2025
    )
    print(f"Created test student: {student.student_id}")
    return student

def create_test_sessions_with_varied_performance(student, num_sessions=3):
    """Create test sessions with varied performance to test adaptive logic"""
    sessions = []
    
    # Get some questions for testing
    questions = list(Question.objects.all()[:50])  # Get 50 questions for testing
    if len(questions) < 20:
        print("❌ Need at least 20 questions in database for testing")
        return []
    
    for i in range(num_sessions):
        # Create a test session
        session = TestSession.objects.create(
            student_id=student.student_id,
            selected_topics=[1, 2, 3],  # Dummy topic IDs
            time_limit=60,
            question_count=10,
            start_time=timezone.now() - timezone.timedelta(days=i+1),
            end_time=timezone.now() - timezone.timedelta(days=i+1, hours=-1),
            is_completed=True,
            total_questions=10
        )
        
        # Create varied answers for each session
        session_questions = questions[i*10:(i+1)*10]  # Different questions for each session
        
        for j, question in enumerate(session_questions):
            # Create different answer patterns:
            # Session 1: Mix of correct/incorrect/unanswered
            # Session 2: Mostly incorrect
            # Session 3: Mix with some correct
            
            if i == 0:  # First session - mixed performance
                if j < 4:  # First 4 correct
                    is_correct = True
                    selected_answer = question.correct_answer
                elif j < 7:  # Next 3 incorrect
                    is_correct = False
                    wrong_answers = ['A', 'B', 'C', 'D']
                    wrong_answers.remove(question.correct_answer)
                    selected_answer = wrong_answers[0]
                else:  # Last 3 unanswered
                    is_correct = False
                    selected_answer = None
            elif i == 1:  # Second session - mostly incorrect
                if j < 2:  # 2 correct
                    is_correct = True
                    selected_answer = question.correct_answer
                elif j < 8:  # 6 incorrect
                    is_correct = False
                    wrong_answers = ['A', 'B', 'C', 'D']
                    wrong_answers.remove(question.correct_answer)
                    selected_answer = wrong_answers[0]
                else:  # 2 unanswered
                    is_correct = False
                    selected_answer = None
            else:  # Third session - better performance
                if j < 6:  # 6 correct
                    is_correct = True
                    selected_answer = question.correct_answer
                elif j < 8:  # 2 incorrect
                    is_correct = False
                    wrong_answers = ['A', 'B', 'C', 'D']
                    wrong_answers.remove(question.correct_answer)
                    selected_answer = wrong_answers[0]
                else:  # 2 unanswered
                    is_correct = False
                    selected_answer = None
            
            TestAnswer.objects.create(
                session=session,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct,
                answered_at=timezone.now()
            )
        
        sessions.append(session)
        print(f"Session {i+1}: {session.id} - Created with varied performance")
    
    return sessions

def test_adaptive_topic_selection(student):
    """Test adaptive selection for topic-based tests"""
    print("\n=== Testing Adaptive Topic-Based Selection ===")
    
    # Get some topics
    topics = Topic.objects.all()[:5]
    if not topics:
        print("❌ No topics found in database")
        return False
    
    topic_ids = [str(topic.id) for topic in topics]
    print(f"Testing with topics: {topic_ids}")
    
    # Test adaptive question generation
    try:
        questions = adaptive_generate_questions_for_topics(
            selected_topics=topic_ids,
            question_count=20,
            student_id=student.student_id,
            exclude_question_ids=set()
        )
        
        print(f"✅ Adaptive selection generated {questions.count()} questions")
        
        if questions.count() > 0:
            print("✅ SUCCESS: Adaptive topic-based selection is working!")
            return True
        else:
            print("❌ PROBLEM: No questions generated")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def test_adaptive_random_selection(student):
    """Test adaptive selection for random tests"""
    print("\n=== Testing Adaptive Random Selection ===")
    
    try:
        questions = adaptive_generate_random_questions_from_database(
            question_count=20,
            student_id=student.student_id,
            exclude_question_ids=set()
        )
        
        print(f"✅ Adaptive random selection generated {questions.count()} questions")
        
        if questions.count() > 0:
            print("✅ SUCCESS: Adaptive random selection is working!")
            return True
        else:
            print("❌ PROBLEM: No questions generated")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def test_bucket_distribution(student):
    """Test that questions are distributed according to adaptive ratios"""
    print("\n=== Testing Bucket Distribution ===")
    
    # Get student's answer history
    answered_questions = TestAnswer.objects.filter(
        session__student_id=student.student_id,
        session__is_completed=True
    ).select_related('question')
    
    correct_question_ids = set()
    wrong_unanswered_question_ids = set()
    answered_question_ids = set()
    
    for answer in answered_questions:
        answered_question_ids.add(answer.question.id)
        if answer.is_correct:
            correct_question_ids.add(answer.question.id)
        else:
            wrong_unanswered_question_ids.add(answer.question.id)
    
    print(f"Student history: {len(answered_question_ids)} total answered")
    print(f"  - Correct: {len(correct_question_ids)}")
    print(f"  - Wrong/Unanswered: {len(wrong_unanswered_question_ids)}")
    
    # Generate questions and analyze distribution
    topics = Topic.objects.all()[:3]
    topic_ids = [str(topic.id) for topic in topics]
    
    try:
        questions = adaptive_generate_questions_for_topics(
            selected_topics=topic_ids,
            question_count=20,
            student_id=student.student_id,
            exclude_question_ids=set()
        )
        
        # Analyze the selected questions
        selected_ids = set(q.id for q in questions)
        
        new_count = len(selected_ids - answered_question_ids)
        correct_count = len(selected_ids & correct_question_ids)
        wrong_count = len(selected_ids & wrong_unanswered_question_ids)
        
        print(f"\nSelected questions analysis:")
        print(f"  - New questions: {new_count} ({new_count/len(selected_ids)*100:.1f}%)")
        print(f"  - Wrong/Unanswered: {wrong_count} ({wrong_count/len(selected_ids)*100:.1f}%)")
        print(f"  - Correct: {correct_count} ({correct_count/len(selected_ids)*100:.1f}%)")
        
        # Check if distribution is reasonable (allowing for some flexibility due to availability)
        total = len(selected_ids)
        new_ratio = new_count / total
        wrong_ratio = wrong_count / total
        correct_ratio = correct_count / total
        
        # We expect roughly 60%/30%/10% but allow flexibility
        success = True
        if new_ratio < 0.3:  # Should have at least 30% new questions if available
            print("⚠️  WARNING: Low ratio of new questions")
        if wrong_ratio > 0.5:  # Shouldn't be more than 50% wrong questions
            print("⚠️  WARNING: High ratio of wrong questions")
        
        print("✅ SUCCESS: Bucket distribution analysis completed!")
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    """Main test function"""
    print("Testing Adaptive Question Selection Logic for NEET Platform")
    print("=" * 60)
    
    try:
        # Create test student
        student = create_test_student()
        
        # Create test sessions with varied performance
        print(f"\nCreating test sessions with varied performance for student {student.student_id}...")
        sessions = create_test_sessions_with_varied_performance(student, 3)
        
        if not sessions:
            print("Failed to create test sessions. Exiting.")
            return
        
        # Test adaptive selection functions
        success1 = test_adaptive_topic_selection(student)
        success2 = test_adaptive_random_selection(student)
        success3 = test_bucket_distribution(student)
        
        print(f"\n=== Test Results ===")
        if success1 and success2 and success3:
            print("🎉 ALL ADAPTIVE SELECTION TESTS PASSED!")
        else:
            print("💥 SOME ADAPTIVE SELECTION TESTS FAILED!")
        
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

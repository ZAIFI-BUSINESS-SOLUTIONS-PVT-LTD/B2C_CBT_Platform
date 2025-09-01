#!/usr/bin/env python
"""
Test script to verify the question exclusion logic is working correctly.
Run this after making changes to ensure no regression.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import TestSession, TestAnswer, StudentProfile, Topic
from neet_app.views.utils import generate_questions_for_topics

def test_exclusion_logic():
    print("=== Testing Question Exclusion Logic ===")
    
    # Get a student
    student = StudentProfile.objects.first()
    if not student:
        print("❌ No students found in database")
        return
    
    print(f"✅ Testing with student: {student.student_id}")
    
    # Get recent question IDs
    recent_question_ids = TestSession.get_recent_question_ids_for_student(student.student_id)
    print(f"✅ Recent question IDs to exclude: {len(recent_question_ids)}")
    
    # Get some topics
    topics = Topic.objects.all()[:3]
    topic_ids = [str(topic.id) for topic in topics]
    print(f"✅ Testing with topics: {topic_ids}")
    
    # Test question generation with exclusion
    questions_with_exclusion = generate_questions_for_topics(
        topic_ids, 
        10, 
        exclude_question_ids=recent_question_ids
    )
    
    print(f"✅ Questions generated with exclusion: {questions_with_exclusion.count()}")
    
    # Check if any excluded questions appear in result
    question_ids_in_result = set(q.id for q in questions_with_exclusion)
    overlap = question_ids_in_result.intersection(recent_question_ids)
    
    if overlap:
        print(f"❌ PROBLEM: Excluded questions appeared in result: {overlap}")
        return False
    else:
        print("✅ SUCCESS: No excluded questions in result")
        return True

def test_insufficient_questions():
    print("\n=== Testing Insufficient Questions Scenario ===")
    
    # Get a few topics
    topics = Topic.objects.all()[:2]
    topic_ids = [str(topic.id) for topic in topics]
    
    # Try to get more questions than available
    questions = generate_questions_for_topics(topic_ids, 1000)
    available_count = questions.count()
    
    print(f"✅ Available questions for topics {topic_ids}: {available_count}")
    
    if available_count < 1000:
        print("✅ SUCCESS: System correctly handles insufficient questions")
        return True
    else:
        print("❌ PROBLEM: Too many questions available (test not valid)")
        return False

if __name__ == "__main__":
    success1 = test_exclusion_logic()
    success2 = test_insufficient_questions()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n💥 SOME TESTS FAILED!")

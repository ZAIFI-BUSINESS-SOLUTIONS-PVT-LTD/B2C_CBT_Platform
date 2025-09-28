#!/usr/bin/env python
"""
Test script for the new deterministic selection engine.
Run this to verify the implementation works correctly.
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.services.selection_engine import (
    DeterministicSelectionEngine,
    generate_questions_with_rules,
    analyze_student_performance,
    test_deterministic_selection
)
from neet_app.models import Topic, Question, StudentProfile, TestSession


def test_basic_functionality():
    """Test basic functionality of the new engine"""
    print("Testing Deterministic Selection Engine...")
    
    # Test 1: Anonymous selection (no student_id)
    print("\n1. Testing anonymous selection...")
    try:
        engine = DeterministicSelectionEngine()
        topics = list(Topic.objects.values_list('id', flat=True)[:5])
        
        if topics:
            questions = engine.generate_questions(
                selected_topics=topics,
                question_count=10,
                test_type="custom"
            )
            print(f"   Anonymous selection: {questions.count()} questions generated")
        else:
            print("   No topics available for testing")
    except Exception as e:
        print(f"   Error in anonymous selection: {e}")
    
    # Test 2: Test with student_id (if students exist)
    print("\n2. Testing student-based selection...")
    try:
        student = StudentProfile.objects.first()
        if student:
            engine = DeterministicSelectionEngine(
                student_id=student.student_id,
                session_id=1  # Mock session ID
            )
            
            questions = engine.generate_questions(
                selected_topics=topics[:3] if topics else [],
                question_count=5,
                test_type="custom"
            )
            print(f"   Student selection: {questions.count()} questions generated")
            print(f"   Student ID: {student.student_id}")
        else:
            print("   No students available for testing")
    except Exception as e:
        print(f"   Error in student selection: {e}")
    
    # Test 3: Public interface
    print("\n3. Testing public interface...")
    try:
        questions = generate_questions_with_rules(
            selected_topics=topics[:2] if topics else [],
            question_count=3,
            test_type="custom"
        )
        print(f"   Public interface: {questions.count()} questions generated")
    except Exception as e:
        print(f"   Error in public interface: {e}")
    
    # Test 4: Settings validation
    print("\n4. Testing configuration...")
    try:
        from django.conf import settings
        neet_settings = getattr(settings, "NEET_SETTINGS", {})
        print(f"   USE_RULE_ENGINE: {neet_settings.get('USE_RULE_ENGINE', 'not set')}")
        print(f"   EXCLUSION_DAYS: {neet_settings.get('EXCLUSION_DAYS', 'not set')}")
        print(f"   WEAK_TOPIC_RATIO: {neet_settings.get('WEAK_TOPIC_RATIO', 'not set')}")
    except Exception as e:
        print(f"   Error reading settings: {e}")


def test_deterministic_behavior():
    """Test that selection is deterministic"""
    print("\n5. Testing deterministic behavior...")
    try:
        student = StudentProfile.objects.first()
        topics = list(Topic.objects.values_list('id', flat=True)[:3])
        
        if student and topics:
            # Run same selection twice
            engine1 = DeterministicSelectionEngine(
                student_id=student.student_id,
                session_id=42  # Fixed session ID
            )
            engine2 = DeterministicSelectionEngine(
                student_id=student.student_id,
                session_id=42  # Same session ID
            )
            
            questions1 = engine1.generate_questions(
                selected_topics=topics,
                question_count=5,
                test_type="custom"
            )
            questions2 = engine2.generate_questions(
                selected_topics=topics,
                question_count=5,
                test_type="custom"
            )
            
            ids1 = list(questions1.values_list('id', flat=True))
            ids2 = list(questions2.values_list('id', flat=True))
            
            if ids1 == ids2:
                print("   ✓ Deterministic behavior confirmed - same results")
            else:
                print("   ✗ Non-deterministic behavior detected!")
                print(f"   Run 1: {ids1}")
                print(f"   Run 2: {ids2}")
        else:
            print("   Skipped - no student or topics available")
    except Exception as e:
        print(f"   Error in deterministic test: {e}")


def test_statistics_computation():
    """Test student statistics computation"""
    print("\n6. Testing statistics computation...")
    try:
        student = StudentProfile.objects.first()
        if student:
            engine = DeterministicSelectionEngine(student_id=student.student_id)
            stats = engine._compute_student_statistics()
            
            print(f"   Topics with performance data: {len(stats.accuracy_per_topic)}")
            print(f"   Topics with timing data: {len(stats.avg_solve_time_per_topic)}")
            print(f"   Questions seen: {len(stats.last_seen_questions)}")
            
            # Show sample data if available
            if stats.accuracy_per_topic:
                sample_topic = next(iter(stats.accuracy_per_topic))
                accuracy = stats.accuracy_per_topic[sample_topic]
                print(f"   Sample accuracy for topic {sample_topic}: {accuracy:.1f}%")
        else:
            print("   Skipped - no student available")
    except Exception as e:
        print(f"   Error in statistics test: {e}")


def show_database_stats():
    """Show basic database statistics"""
    print("\n7. Database statistics:")
    try:
        print(f"   Topics: {Topic.objects.count()}")
        print(f"   Questions: {Question.objects.count()}")
        print(f"   Students: {StudentProfile.objects.count()}")
        print(f"   Test Sessions: {TestSession.objects.count()}")
        
        # Show sample subjects
        subjects = list(Topic.objects.values_list('subject', flat=True).distinct()[:5])
        print(f"   Sample subjects: {subjects}")
        
        # Show sample difficulties
        difficulties = list(Question.objects.exclude(
            difficulty__isnull=True
        ).values_list('difficulty', flat=True).distinct()[:5])
        print(f"   Sample difficulties: {difficulties}")
        
    except Exception as e:
        print(f"   Error getting database stats: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("DETERMINISTIC SELECTION ENGINE TEST")
    print("=" * 60)
    
    show_database_stats()
    test_basic_functionality()
    test_deterministic_behavior()
    test_statistics_computation()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
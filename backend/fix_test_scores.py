#!/usr/bin/env python3
"""
Script to diagnose and fix test session scores that are showing as None
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from django.db import connection
from neet_app.models import TestSession, TestAnswer, Question

def check_test_scores():
    """Check why test scores are None and calculate them if needed"""
    print("=== INVESTIGATING TEST SCORES ===")
    
    # Get a sample test session
    sample_session = TestSession.objects.filter(
        student_id='STU002407WOK700',
        is_completed=True
    ).first()
    
    if not sample_session:
        print("❌ No completed test sessions found")
        return
    
    print(f"📊 Sample session: {sample_session.id}")
    print(f"   Physics Score: {sample_session.physics_score}")
    print(f"   Chemistry Score: {sample_session.chemistry_score}")
    print(f"   Botany Score: {sample_session.botany_score}")
    print(f"   Zoology Score: {sample_session.zoology_score}")
    print(f"   Start Time: {sample_session.start_time}")
    print(f"   End Time: {sample_session.end_time}")
    print(f"   Completed: {sample_session.is_completed}")
    
    # Check test answers for this session
    answers = TestAnswer.objects.filter(session_id=sample_session.id)
    print(f"📝 Total answers: {answers.count()}")
    
    if answers.count() > 0:
        correct_answers = answers.filter(is_correct=True).count()
        total_answers = answers.count()
        overall_percentage = (correct_answers / total_answers) * 100
        
        print(f"✅ Correct answers: {correct_answers}/{total_answers}")
        print(f"📊 Overall percentage: {overall_percentage:.1f}%")
        
        # Check subject-wise breakdown
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
        
        for subject in subjects:
            # Get questions for this subject through topics
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END) as correct
                    FROM test_answers ta
                    JOIN questions q ON ta.question_id = q.id  
                    JOIN topics t ON q.topic_id = t.id
                    WHERE ta.session_id = %s AND t.subject = %s
                """, [sample_session.id, subject])
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    total, correct = result
                    percentage = (correct / total) * 100
                    print(f"🧪 {subject}: {correct}/{total} = {percentage:.1f}%")
                else:
                    print(f"🧪 {subject}: No questions found")

def fix_test_scores():
    """Calculate and update missing test scores"""
    print("\n=== FIXING TEST SCORES ===")
    
    # Get all completed sessions with None scores
    sessions_to_fix = TestSession.objects.filter(
        student_id='STU002407WOK700',
        is_completed=True,
        physics_score__isnull=True
    )
    
    print(f"🔧 Found {sessions_to_fix.count()} sessions to fix")
    
    for session in sessions_to_fix:
        print(f"\n📊 Fixing session {session.id}...")
        
        # Calculate subject-wise scores
        subjects = {
            'Physics': 'physics_score',
            'Chemistry': 'chemistry_score', 
            'Botany': 'botany_score',
            'Zoology': 'zoology_score'
        }
        
        scores = {}
        
        for subject, field in subjects.items():
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END) as correct
                    FROM test_answers ta
                    JOIN questions q ON ta.question_id = q.id  
                    JOIN topics t ON q.topic_id = t.id
                    WHERE ta.session_id = %s AND t.subject = %s
                """, [session.id, subject])
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    total, correct = result
                    percentage = (correct / total) * 100
                    scores[field] = round(percentage, 1)
                    print(f"   {subject}: {correct}/{total} = {percentage:.1f}%")
                else:
                    scores[field] = None
                    print(f"   {subject}: No questions")
        
        # Update the session
        if any(score is not None for score in scores.values()):
            for field, score in scores.items():
                setattr(session, field, score)
            
            session.save()
            print(f"✅ Updated session {session.id}")
        else:
            print(f"⚠️ No valid scores to update for session {session.id}")

def verify_fix():
    """Verify that scores have been fixed"""
    print("\n=== VERIFYING FIX ===")
    
    sessions = TestSession.objects.filter(
        student_id='STU002407WOK700',
        is_completed=True
    ).order_by('-start_time')[:5]
    
    for session in sessions:
        print(f"📊 Session {session.id}:")
        print(f"   Physics: {session.physics_score}%")
        print(f"   Chemistry: {session.chemistry_score}%") 
        print(f"   Botany: {session.botany_score}%")
        print(f"   Zoology: {session.zoology_score}%")

if __name__ == "__main__":
    check_test_scores()
    fix_test_scores() 
    verify_fix()

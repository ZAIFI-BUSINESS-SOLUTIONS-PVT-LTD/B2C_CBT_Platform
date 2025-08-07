#!/usr/bin/env python
"""
Utility script to update subject scores for all completed test sessions
This can be run as a one-time migration or periodic maintenance task
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import TestSession
from django.db import transaction

def update_all_subject_scores():
    """Update subject scores for all completed test sessions"""
    print("🔄 Updating subject scores for all completed test sessions...")
    
    # Get all completed test sessions
    completed_sessions = TestSession.objects.filter(is_completed=True)
    total_sessions = completed_sessions.count()
    
    print(f"📊 Found {total_sessions} completed test sessions")
    
    if total_sessions == 0:
        print("✅ No completed sessions found to update")
        return
    
    updated_count = 0
    failed_count = 0
    
    with transaction.atomic():
        for i, session in enumerate(completed_sessions, 1):
            try:
                print(f"📝 Processing session {i}/{total_sessions} - ID: {session.id} - Student: {session.student_id}")
                
                # Calculate and update subject scores
                subject_stats = session.calculate_and_update_subject_scores()
                
                # Show results
                session.refresh_from_db()
                print(f"   ✅ Updated - Physics: {session.physics_score}, Chemistry: {session.chemistry_score}")
                print(f"              Botany: {session.botany_score}, Zoology: {session.zoology_score}")
                
                updated_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to update session {session.id}: {e}")
                failed_count += 1
                continue
    
    print(f"\n📈 Summary:")
    print(f"   ✅ Successfully updated: {updated_count} sessions")
    print(f"   ❌ Failed to update: {failed_count} sessions")
    print(f"   📊 Total processed: {updated_count + failed_count}/{total_sessions}")

def update_specific_student_scores(student_id: str):
    """Update subject scores for a specific student's completed test sessions"""
    print(f"🔄 Updating subject scores for student: {student_id}")
    
    # Get completed test sessions for this student
    completed_sessions = TestSession.objects.filter(
        student_id=student_id, 
        is_completed=True
    ).order_by('start_time')
    
    total_sessions = completed_sessions.count()
    print(f"📊 Found {total_sessions} completed test sessions for {student_id}")
    
    if total_sessions == 0:
        print("✅ No completed sessions found for this student")
        return
    
    for i, session in enumerate(completed_sessions, 1):
        try:
            print(f"📝 Processing session {i}/{total_sessions} - ID: {session.id}")
            print(f"   Started: {session.start_time}")
            
            # Show before
            print(f"   Before - Physics: {session.physics_score}, Chemistry: {session.chemistry_score}")
            print(f"            Botany: {session.botany_score}, Zoology: {session.zoology_score}")
            
            # Calculate and update subject scores
            subject_stats = session.calculate_and_update_subject_scores()
            
            # Show after
            session.refresh_from_db()
            print(f"   After  - Physics: {session.physics_score}, Chemistry: {session.chemistry_score}")
            print(f"            Botany: {session.botany_score}, Zoology: {session.zoology_score}")
            
            # Show detailed stats
            print(f"   Stats:")
            for subject, stats in subject_stats.items():
                if stats['total_questions'] > 0:
                    raw_score = (stats['correct'] * 4) + (stats['wrong'] * -1)
                    print(f"      {subject}: {stats['correct']}C/{stats['wrong']}W/{stats['unanswered']}U = {raw_score}/{stats['total_questions']*4}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Failed to update session {session.id}: {e}")
            continue

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Update specific student
        student_id = sys.argv[1]
        update_specific_student_scores(student_id)
    else:
        # Update all sessions
        confirmation = input("This will update ALL completed test sessions. Continue? (y/N): ")
        if confirmation.lower() == 'y':
            update_all_subject_scores()
        else:
            print("Operation cancelled.")

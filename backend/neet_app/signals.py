"""
Django signals for automatic data processing in NEET app models
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import StudentProfile, TestSession
from .views.insights_views import get_student_insights

# Global set to track processed sessions to prevent infinite loops
_processed_sessions = set()


@receiver(post_save, sender=TestSession)
def update_subject_scores_on_completion(sender, instance, created, **kwargs):
    """
    Automatically update subject scores when a test session is marked as completed.
    
    **Important**: This signal now has minimal responsibility. The main test processing
    pipeline (compute results → zone insights → student insights) is handled by the
    process_test_submission_task orchestrator enqueued from the submit() endpoint.
    
    This signal only:
    1. Updates subject-level scores for the session
    2. Skips duplicate processing using in-process cache
    
    The orchestrator task in tasks.py handles all heavy processing on workers.
    """
    # Create unique key for this session and operation
    session_key = f"scores_{instance.id}_{instance.is_completed}"
    
    # Only process if the session is completed and hasn't been processed yet
    if instance.is_completed and session_key not in _processed_sessions:
        _processed_sessions.add(session_key)
        
        try:
            # Check if there are any test answers for this session
            from .models import TestAnswer
            answer_count = TestAnswer.objects.filter(session=instance).count()
            
            if answer_count > 0:
                print(f"🔄 Auto-updating subject scores for completed session {instance.id}")
                instance.calculate_and_update_subject_scores()
                print(f"✅ Subject scores updated for session {instance.id}")
                
                # NOTE: Insights generation is now handled by process_test_submission_task
                # orchestrator enqueued from submit() endpoint. We don't duplicate that here
                # to avoid race conditions and duplicate work.
                print(f"ℹ️ Insights pipeline will be handled by orchestrator task for session {instance.id}")
            else:
                print(f"⚠️ No answers found for session {instance.id}, skipping score calculation")
                
        except Exception as e:
            print(f"❌ Failed to auto-update subject scores for session {instance.id}: {e}")
        finally:
            # Clean up old entries to prevent memory issues
            if len(_processed_sessions) > 1000:
                _processed_sessions.clear()


@receiver(pre_save, sender=StudentProfile)
def generate_student_credentials(sender, instance, **kwargs):
    """
    Auto-generate student_id before saving StudentProfile
    Password generation is now handled by user input, not automatic generation
    """
    if not instance.student_id and instance.full_name and instance.date_of_birth:
        # Only generate student_id, password is now user-defined
        instance.generate_credentials()


@receiver(post_save, sender=TestSession)
def classify_test_session_topics(sender, instance, created, **kwargs):
    """
    Classify selected topics by subjects after TestSession is saved
    """
    # Create unique key for this session and operation
    classify_key = f"classify_{instance.id}_{created}"
    
    if classify_key not in _processed_sessions and (created or not all([
        instance.physics_topics,
        instance.chemistry_topics,
        instance.botany_topics,
        instance.zoology_topics,
        instance.biology_topics
    ])):
        _processed_sessions.add(classify_key)
        
        try:
            instance.update_subject_classification()
            # Use update() to avoid triggering signals again
            TestSession.objects.filter(id=instance.id).update(
                physics_topics=instance.physics_topics,
                chemistry_topics=instance.chemistry_topics,
                botany_topics=instance.botany_topics,
                zoology_topics=instance.zoology_topics,
                biology_topics=instance.biology_topics
            )
        except Exception as e:
            print(f"❌ Failed to classify topics for session {instance.id}: {e}")


@receiver(post_save, sender=TestSession)
def update_student_statistics(sender, instance, **kwargs):
    """
    Update student statistics when a test session is completed
    """
    # Create unique key for this session and operation
    stats_key = f"stats_{instance.id}_{instance.is_completed}"
    
    if instance.is_completed and stats_key not in _processed_sessions:
        _processed_sessions.add(stats_key)
        
        try:
            student_profile = StudentProfile.objects.get(student_id=instance.student_id)
            # Update last login timestamp when a test is completed
            from django.utils import timezone
            StudentProfile.objects.filter(student_id=instance.student_id).update(
                last_login=timezone.now()
            )
        except StudentProfile.DoesNotExist:
            pass  # Student profile doesn't exist, skip statistics update
        except Exception as e:
            print(f"❌ Failed to update statistics for session {instance.id}: {e}")

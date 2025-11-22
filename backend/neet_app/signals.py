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
    Automatically update subject scores when a test session is marked as completed
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

                # Generate insights after score calculation (only once per completion)
                insights_key = f"insights_{instance.id}_{instance.student_id}"
                if insights_key not in _processed_sessions:
                    _processed_sessions.add(insights_key)
                    
                    try:
                        # Prefer asynchronous enqueue via Celery task so this signal handler returns quickly.
                        # If Celery isn't available or enqueuing fails, fall back to the previous synchronous call.
                        try:
                            from .tasks import generate_insights_task
                            from .views.insights_views import is_celery_worker_available
                            
                            # Check if Celery workers are available before enqueueing
                            if not is_celery_worker_available():
                                print(f"⚠️ No active Celery workers detected, falling back to synchronous insights generation for student {instance.student_id}")
                                raise RuntimeError("No active Celery workers available")
                            else:
                                # Use the same signature as the view: (student_id, request_data, force_regenerate)
                                request_data = {'force_regenerate': True}
                                generate_insights_task.delay(instance.student_id, request_data, True)
                                print(f"🔄 Enqueued generate_insights_task for student {instance.student_id} after test {instance.id}")
                                
                                # Generate zone insights (new feature - independent of existing 4 cards)
                                try:
                                    from .tasks import generate_zone_insights_task
                                    generate_zone_insights_task.delay(instance.id)
                                    print(f"🎯 Enqueued zone insights task for test {instance.id}")
                                except Exception as zone_e:
                                    print(f"⚠️ Failed to enqueue zone insights (non-critical): {zone_e}")
                                
                        except (ImportError, RuntimeError, Exception) as e:
                            # Celery not installed/available in this environment or no workers, fall back to background thread
                            if isinstance(e, ImportError):
                                print("⚠️ Celery not available, falling back to background insights generation")
                            else:
                                print(f"⚠️ Celery issue ({str(e)}), falling back to background insights generation")
                                
                            # Run insights generation in background thread to avoid blocking response
                            import threading
                            
                            def generate_insights_background():
                                try:
                                    from rest_framework.test import APIRequestFactory
                                    import json
                                    factory = APIRequestFactory()
                                    request_data = {'force_regenerate': True}
                                    request = factory.post('/api/insights/student/', data=json.dumps(request_data), content_type='application/json')

                                    class MockUser:
                                        def __init__(self, student_id):
                                            self.student_id = student_id
                                            self.is_authenticated = True
                                            self.is_active = True
                                    request.user = MockUser(instance.student_id)

                                    print(f"🔄 Background thread: Generating insights for student {instance.student_id} after test {instance.id}")
                                    response = get_student_insights(request)
                                    if response.status_code == 200:
                                        print(f"✅ Background insights generated and cached for student {instance.student_id} after test completion.")
                                    else:
                                        print(f"⚠️ Background insights generation returned status {response.status_code} for student {instance.student_id}")
                                except Exception as bg_e:
                                    print(f"❌ Background insights generation failed for student {instance.student_id}: {bg_e}")
                            
                            # Start background thread (daemon=True so it doesn't block app shutdown)
                            thread = threading.Thread(target=generate_insights_background, daemon=True)
                            thread.start()
                            print(f"🚀 Started background insights generation for student {instance.student_id} after test {instance.id}")
                    except Exception as e:
                        # Catch any unexpected exception from enqueue or synchronous call and log, but don't raise
                        print(f"❌ Failed to trigger insights for student {instance.student_id}: {e}")
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

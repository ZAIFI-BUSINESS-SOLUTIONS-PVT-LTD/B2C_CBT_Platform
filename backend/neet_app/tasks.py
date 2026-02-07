"""
Celery tasks for asynchronous processing.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    # Fallback decorator if Celery not installed
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    CELERY_AVAILABLE = False
    logger.warning("Celery not available - tasks will run synchronously")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    name='neet_app.tasks.generate_misconceptions_task'
)
def generate_misconceptions_task(self, test_id: int):
    """
    Generate misconceptions for all MCQ questions in a test.
    Runs asynchronously after test upload.
    
    Args:
        test_id: PlatformTest ID
        
    Returns:
        Dict with processing statistics
    """
    from django.utils import timezone
    from .models import PlatformTest
    
    try:
        # Update test status to 'processing'
        try:
            test = PlatformTest.objects.get(id=test_id)
            test.misconception_generation_status = 'processing'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
        except PlatformTest.DoesNotExist:
            logger.error(f'Test {test_id} not found')
            return {'status': 'error', 'error': 'Test not found'}
        
        from .services.misconception_service import generate_misconceptions_for_test
        
        logger.info(f'🧠 Generating misconceptions for test {test_id}')
        print(f"🧠 Starting misconception generation for test {test_id}")
        
        # Generate misconceptions
        result = generate_misconceptions_for_test(test_id, batch_size=20)
        
        if result['success']:
            # Update status to 'completed'
            test.misconception_generation_status = 'completed'
            test.misconception_generated_at = timezone.now()
            test.save(update_fields=['misconception_generation_status', 'misconception_generated_at', 'updated_at'])
            
            logger.info(
                f'✅ Misconceptions generated for test {test_id}: '
                f'{result["processed"]}/{result["total_questions"]} questions processed, '
                f'{result["failed"]} failed, '
                f'subjects: {", ".join(result["subjects_processed"])}'
            )
            print(
                f"✅ Misconceptions complete: {result['processed']}/{result['total_questions']} questions, "
                f"{result['failed']} failed"
            )
        else:
            # Update status to 'failed'
            test.misconception_generation_status = 'failed'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
            
            logger.error(f'❌ Misconception generation failed for test {test_id}: {result.get("error")}')
            print(f"❌ Misconception generation failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        # Update status to 'failed' on exception
        try:
            test = PlatformTest.objects.get(id=test_id)
            test.misconception_generation_status = 'failed'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
        except:
            pass
        
        logger.exception(f'generate_misconceptions_task failed for test {test_id}')
        print(f"❌ Misconception task error: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'test_id': test_id,
            'total_questions': 0,
            'processed': 0,
            'failed': 0
        }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    name='neet_app.tasks.generate_zone_insights_task'
)
def generate_zone_insights_task(self, session_id: int):
    """
    Generate zone insights for a completed test session.
    Runs asynchronously after test submission to avoid blocking the submit endpoint.
    
    Args:
        session_id: TestSession ID
        
    Returns:
        Dict with processing statistics
    """
    from .models import TestSession
    
    try:
        # Verify session exists
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'TestSession {session_id} not found')
            return {'status': 'error', 'error': 'Session not found'}
        
        from .services.zone_insights_service import generate_all_subject_zones
        
        logger.info(f'🎯 Generating zone insights for test session {session_id}')
        print(f"🎯 Starting zone insights generation for session {session_id}")
        
        # Generate zone insights for all subjects
        zone_results = generate_all_subject_zones(session_id)
        
        if zone_results:
            logger.info(
                f'✅ Zone insights generated for session {session_id}: '
                f'{len(zone_results)} subjects processed'
            )
            print(f"✅ Zone insights complete: {len(zone_results)} subjects processed")
            return {
                'status': 'success',
                'session_id': session_id,
                'subjects_processed': len(zone_results),
                'subjects': [r.get('subject') for r in zone_results if isinstance(r, dict)]
            }
        else:
            logger.warning(f'⚠️ No zone insights generated for session {session_id}')
            print(f"⚠️ No zone insights generated for session {session_id}")
            return {
                'status': 'warning',
                'session_id': session_id,
                'message': 'No zone insights generated'
            }
        
    except Exception as e:
        logger.exception(f'generate_zone_insights_task failed for session {session_id}')
        print(f"❌ Zone insights generation failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'session_id': session_id
        }

from __future__ import annotations
import logging
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Import project internals where heavy work lives
from .views import insights_views
from .services.ai.gemini_client import GeminiClient
from .services.ai.sql_agent import SQLAgent
from typing import Dict, Optional


@shared_task(bind=True)
def generate_insights_task(self, student_id: str, request_data: dict = None, force_regenerate: bool = False):
    """Wrapper task to generate and save student insights.

    This calls the existing synchronous logic in `insights_views` helpers so we don't duplicate HTTP handling.
    """
    try:
        thresholds = insights_views.get_thresholds(request_data)
        all_metrics = insights_views.calculate_topic_metrics(student_id)

        if not all_metrics or 'topics' not in all_metrics:
            empty_response = {
                'status': 'success',
                'data': {
                    'strength_topics': [],
                    'weak_topics': [],
                    'improvement_topics': [],
                    'last_test_topics': [],
                    'unattempted_topics': [],
                    'thresholds_used': thresholds,
                    'summary': {
                        'total_topics_analyzed': 0,
                        'total_tests_taken': 0,
                        'unattempted_topics_count': 0,
                        'message': 'No test data available for analysis'
                    },
                    'cached': False
                }
            }
            insights_views.save_insights_to_database(student_id, empty_response)
            return empty_response

        classification = insights_views.classify_topics(
            all_metrics['topics'], all_metrics.get('overall_avg_time', 0), thresholds
        )

        last_test_data = insights_views.get_last_test_metrics(student_id, thresholds)

        llm_insights = {}
        if classification.get('strength_topics'):
            llm_insights['strengths'] = insights_views.generate_llm_insights('strengths', classification['strength_topics'])
        if classification.get('weak_topics'):
            llm_insights['weaknesses'] = insights_views.generate_llm_insights('weaknesses', classification['weak_topics'])

        unattempted_topics = insights_views.get_unattempted_topics(all_metrics['topics'])
        study_plan_data = {
            'weak_topics': classification.get('weak_topics', []),
            'improvement_topics': classification.get('improvement_topics', []),
            'strength_topics': classification.get('strength_topics', []),
            'unattempted_topics': unattempted_topics
        }
        llm_insights['study_plan'] = insights_views.generate_llm_insights('study_plan', study_plan_data)

        if last_test_data.get('last_test_topics'):
            llm_insights['last_test_feedback'] = insights_views.generate_llm_insights('last_test_feedback', last_test_data['last_test_topics'])

        total_topics = len(all_metrics['topics'])
        from .models import TestSession
        total_tests = TestSession.objects.filter(student_id=student_id, is_completed=True).count()
        latest_session = TestSession.objects.filter(student_id=student_id, is_completed=True).order_by('-end_time').first()
        latest_session_id = latest_session.id if latest_session else None

        summary = {
            'total_topics_analyzed': total_topics,
            'total_tests_taken': total_tests,
            'strengths_count': len(classification.get('strength_topics', [])),
            'weaknesses_count': len(classification.get('weak_topics', [])),
            'improvements_count': len(classification.get('improvement_topics', [])),
            'unattempted_topics_count': len(unattempted_topics),
            'overall_avg_time': round(all_metrics.get('overall_avg_time', 0), 2),
            'last_session_id': latest_session_id
        }

        response_data = {
            'status': 'success',
            'data': {
                **classification,
                **last_test_data,
                'unattempted_topics': unattempted_topics,
                'llm_insights': llm_insights,
                'thresholds_used': thresholds,
                'summary': summary,
                'cached': False
            }
        }

        insights_views.save_insights_to_database(student_id, response_data, latest_session_id)
        return response_data
    except Exception:
        logger.exception('generate_insights_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    soft_time_limit=60,
    time_limit=120,
)
def gemini_generate_task(self, prompt: str, max_retries: int = 3):
    """Run Gemini AI generation in background using the project's GeminiClient wrapper.

    Notes:
    - Automatic retries with exponential backoff on exceptions (max 3 retries).
    - Soft/hard time limits to avoid workers hanging on slow LLM calls.
    - Keeps logging and re-raises so Celery's autoretry handles retrying.
    """
    try:
        client = GeminiClient()
        return client.generate_response(prompt, max_retries=max_retries)
    except Exception:
        logger.exception('gemini_generate_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=30,
    time_limit=60,
)
def sql_agent_generate_task(self, student_id: str, user_message: str):
    """Generate SQL via the SQLAgent in background.

    - Retries on failure (2 attempts) with backoff.
    - Shorter time limits than full LLM generation since SQL generation should be quicker.
    """
    try:
        agent = SQLAgent()
        status, sql = agent.generate_sql_query(student_id, user_message)
        return {'status': status, 'sql': sql}
    except Exception:
        logger.exception('sql_agent_generate_task failed')
        raise


@shared_task(bind=True)
def send_welcome_email_task(self, user_id: str):
    """Task wrapper to send welcome email for a StudentProfile by student_id."""
    try:
        # Import locally to avoid circular imports at module import time
        from .models import StudentProfile
        from .notifications import _render_welcome_templates, _send_email_sync

        user = StudentProfile.objects.get(student_id=user_id)
        frontend_base = getattr(__import__('django.conf').conf.settings, 'FRONTEND_URL', None) or getattr(__import__('django.conf').conf.settings, 'FRONTEND_RESET_URL', None)
        context = {
            'user': user,
            'full_name': user.full_name,
            'login_url': (frontend_base or 'https://neet.inzighted.com') + '/',
            'support_email': 'support@inzighted.com',
        }
        rendered = _render_welcome_templates(user, context)
        return _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
    except Exception:
        logger.exception('send_welcome_email_task failed')
        raise


@shared_task(bind=True)
def send_test_result_email_task(self, user_id: str, results: Dict):
    try:
        from .models import StudentProfile
        from .notifications import _render_test_result_templates, _send_email_sync

        user = StudentProfile.objects.get(student_id=user_id)
        frontend_base = getattr(__import__('django.conf').conf.settings, 'FRONTEND_URL', None) or getattr(__import__('django.conf').conf.settings, 'FRONTEND_RESET_URL', None)
        context = {
            'user': user,
            'full_name': user.full_name,
            'session_id': results.get('session_id'),
            'total_questions': results.get('total_questions'),
            'correct_answers': results.get('correct_answers'),
            'incorrect_answers': results.get('incorrect_answers'),
            'unanswered_questions': results.get('unanswered_questions'),
            'time_taken': results.get('time_taken'),
            'score_percentage': results.get('score_percentage'),
            'results_url': f"{(frontend_base or 'https://neet.inzighted.com')}/results/{results.get('session_id')}",
            'support_email': 'support@inzighted.com',
        }
        rendered = _render_test_result_templates(user, context)
        return _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
    except Exception:
        logger.exception('send_test_result_email_task failed')
        raise


@shared_task(bind=True)
def send_inactivity_reminder_task(self, user_id: str, last_test_date: Optional[str] = None):
    try:
        from .models import StudentProfile
        from .notifications import _render_inactivity_templates, _send_email_sync

        user = StudentProfile.objects.get(student_id=user_id)
        frontend_base = getattr(__import__('django.conf').conf.settings, 'FRONTEND_URL', None) or getattr(__import__('django.conf').conf.settings, 'FRONTEND_RESET_URL', None)
        context = {
            'user': user,
            'full_name': user.full_name,
            'last_test_date': last_test_date,
            'dashboard_url': (frontend_base or 'https://neet.inzighted.com') + '/',
            'support_email': 'support@inzighted.com',
        }
        rendered = _render_inactivity_templates(user, context)
        return _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
    except Exception:
        logger.exception('send_inactivity_reminder_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=120,
    time_limit=240,
)
def dashboard_analytics_task(self, student_id: str):
    """Background task to generate dashboard analytics for a student."""
    try:
        from .models import StudentProfile
        from .views.dashboard_views import dashboard_analytics
        from rest_framework.test import APIRequestFactory
        
        # Verify student exists
        user = StudentProfile.objects.get(student_id=student_id)
        
        # Create mock request with authenticated student
        factory = APIRequestFactory()
        request = factory.get('/api/dashboard/analytics/')
        
        class MockUser:
            def __init__(self, student_id):
                self.student_id = student_id
                self.is_authenticated = True
                self.is_active = True
        
        request.user = MockUser(student_id)
        
        # Call the analytics view
        response = dashboard_analytics(request)
        
        if response.status_code == 200:
            logger.info(f'Dashboard analytics generated successfully for student {student_id}')
            return response.data
        else:
            logger.error(f'Dashboard analytics failed with status {response.status_code} for student {student_id}')
            raise Exception(f'Analytics generation failed with status {response.status_code}')
            
    except Exception:
        logger.exception('dashboard_analytics_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=120,
    time_limit=240,
)
def dashboard_comprehensive_analytics_task(self, student_id: str):
    """Background task to generate comprehensive dashboard analytics for a student."""
    try:
        from .models import StudentProfile
        from .views.dashboard_views import dashboard_comprehensive_analytics
        from rest_framework.test import APIRequestFactory
        
        # Verify student exists
        user = StudentProfile.objects.get(student_id=student_id)
        
        # Create mock request with authenticated student
        factory = APIRequestFactory()
        request = factory.get('/api/dashboard/comprehensive-analytics/')
        
        class MockUser:
            def __init__(self, student_id):
                self.student_id = student_id
                self.is_authenticated = True
                self.is_active = True
        
        request.user = MockUser(student_id)
        
        # Call the comprehensive analytics view
        response = dashboard_comprehensive_analytics(request)
        
        if response.status_code == 200:
            logger.info(f'Comprehensive analytics generated successfully for student {student_id}')
            return response.data
        else:
            logger.error(f'Comprehensive analytics failed with status {response.status_code} for student {student_id}')
            raise Exception(f'Comprehensive analytics generation failed with status {response.status_code}')
            
    except Exception:
        logger.exception('dashboard_comprehensive_analytics_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=90,
    time_limit=180,
)
def platform_test_analytics_task(self, student_id: str, test_id: str = None):
    """Background task to generate platform test analytics for a student."""
    try:
        from .models import StudentProfile
        from .views.dashboard_views import platform_test_analytics
        from rest_framework.test import APIRequestFactory
        
        # Verify student exists
        user = StudentProfile.objects.get(student_id=student_id)
        
        # Create mock request with authenticated student and optional test_id
        factory = APIRequestFactory()
        url = '/api/dashboard/platform-test-analytics/'
        if test_id:
            url += f'?test_id={test_id}'
        request = factory.get(url)
        
        class MockUser:
            def __init__(self, student_id):
                self.student_id = student_id
                self.is_authenticated = True
                self.is_active = True
        
        request.user = MockUser(student_id)
        
        # Call the platform test analytics view
        response = platform_test_analytics(request)
        
        if response.status_code == 200:
            logger.info(f'Platform test analytics generated successfully for student {student_id}, test_id: {test_id}')
            return response.data
        else:
            logger.error(f'Platform test analytics failed with status {response.status_code} for student {student_id}')
            raise Exception(f'Platform test analytics generation failed with status {response.status_code}')
            
    except Exception:
        logger.exception('platform_test_analytics_task failed')
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    soft_time_limit=90,
    time_limit=180,
)
def chat_generate_task(self, chat_session_id: str, user_message: str, student_id: str):
    """Background task to run chatbot message generation and persist messages.

    Returns the bot response payload.

    - Retries on transient failures (max 3 retries) with backoff.
    - Longer soft/hard timeouts to allow for LLM response generation.
    """
    try:
        from .services.chatbot_service_refactored import NeetChatbotService
        service = NeetChatbotService()
        result = service.generate_response(query=user_message, student_id=student_id, chat_session_id=chat_session_id)
        return result
    except Exception:
        logger.exception('chat_generate_task failed')
        raise

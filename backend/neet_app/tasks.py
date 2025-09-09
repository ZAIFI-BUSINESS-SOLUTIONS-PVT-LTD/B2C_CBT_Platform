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

    This calls the existing synchronous logic in `insights_views.get_student_insights` but
    uses internal helper functions so we don't duplicate HTTP handling.
    """
    try:
        # The heavy function is split into helpers inside insights_views; call the generation flow
        # Reuse existing helpers: calculate metrics, classify, generate LLM insights and save
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
            all_metrics['topics'], all_metrics['overall_avg_time'], thresholds
        )

        last_test_data = insights_views.get_last_test_metrics(student_id, thresholds)

        llm_insights = {}
        if classification['strength_topics']:
            llm_insights['strengths'] = insights_views.generate_llm_insights('strengths', classification['strength_topics'])
        if classification['weak_topics']:
            llm_insights['weaknesses'] = insights_views.generate_llm_insights('weaknesses', classification['weak_topics'])

        unattempted_topics = insights_views.get_unattempted_topics(all_metrics['topics'])
        study_plan_data = {
            'weak_topics': classification['weak_topics'],
            'improvement_topics': classification['improvement_topics'],
            'strength_topics': classification['strength_topics'],
            'unattempted_topics': unattempted_topics
        }
        llm_insights['study_plan'] = insights_views.generate_llm_insights('study_plan', study_plan_data)

        if last_test_data['last_test_topics']:
            llm_insights['last_test_feedback'] = insights_views.generate_llm_insights('last_test_feedback', last_test_data['last_test_topics'])

        total_topics = len(all_metrics['topics'])
        from ..models import TestSession
        total_tests = TestSession.objects.filter(student_id=student_id, is_completed=True).count()
        latest_session = TestSession.objects.filter(student_id=student_id, is_completed=True).order_by('-end_time').first()
        latest_session_id = latest_session.id if latest_session else None

        summary = {
            'total_topics_analyzed': total_topics,
            'total_tests_taken': total_tests,
            'strengths_count': len(classification['strength_topics']),
            'weaknesses_count': len(classification['weak_topics']),
            'improvements_count': len(classification['improvement_topics']),
            'unattempted_topics_count': len(unattempted_topics),
            'overall_avg_time': round(all_metrics['overall_avg_time'], 2),
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
    except Exception as exc:
        logger.exception('generate_insights_task failed')
        raise


@shared_task(bind=True)
def gemini_generate_task(self, prompt: str, max_retries: int = 3):
    """Run Gemini AI generation in background using the project's GeminiClient wrapper."""
    try:
        client = GeminiClient()
        return client.generate_response(prompt, max_retries=max_retries)
    except Exception:
        logger.exception('gemini_generate_task failed')
        raise


@shared_task(bind=True)
def sql_agent_generate_task(self, student_id: str, user_message: str):
    try:
        agent = SQLAgent()
        status, sql = agent.generate_sql_query(student_id, user_message)
        return {'status': status, 'sql': sql}
    except Exception:
        logger.exception('sql_agent_generate_task failed')
        raise


@shared_task(bind=True)
def send_welcome_email_task(self, user_id: int):
    """Task wrapper to send welcome email for a StudentProfile by id."""
    try:
        # Import locally to avoid circular imports at module import time
        from .models import StudentProfile
        from .notifications import _render_welcome_templates, _send_email_sync

        user = StudentProfile.objects.get(id=user_id)
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
def send_test_result_email_task(self, user_id: int, results: Dict):
    try:
        from .models import StudentProfile
        from .notifications import _render_test_result_templates, _send_email_sync

        user = StudentProfile.objects.get(id=user_id)
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
def send_inactivity_reminder_task(self, user_id: int, last_test_date: Optional[str] = None):
    try:
        from .models import StudentProfile
        from .notifications import _render_inactivity_templates, _send_email_sync

        user = StudentProfile.objects.get(id=user_id)
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


@shared_task(bind=True)
def chat_generate_task(self, chat_session_id: str, user_message: str, student_id: str):
    """Background task to run chatbot message generation and persist messages.

    Returns the bot response payload.
    """
    try:
        from .services.chatbot_service_refactored import NeetChatbotService
        service = NeetChatbotService()
        result = service.generate_response(query=user_message, student_id=student_id, chat_session_id=chat_session_id)
        return result
    except Exception:
        logger.exception('chat_generate_task failed')
        raise

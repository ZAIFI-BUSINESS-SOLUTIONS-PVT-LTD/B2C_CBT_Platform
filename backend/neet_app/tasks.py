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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=60,
    time_limit=120,
)
def chat_memory_summarizer_task(self, chat_session_id: str, student_id: str, message_threshold: int = 10):
    """Background task to analyze recent conversation and extract long-term memories.
    
    Args:
        chat_session_id: The chat session to analyze
        student_id: The student ID
        message_threshold: Minimum number of messages before summarization
    
    Returns:
        Dict with summary results
    """
    try:
        from .models import ChatSession, ChatMessage, ChatMemory, StudentProfile
        from .services.ai.gemini_client import GeminiClient
        import json
        
        logger.info(f'Starting memory summarization for session {chat_session_id}, student {student_id}')
        
        # Get the chat session
        try:
            chat_session = ChatSession.objects.get(chat_session_id=chat_session_id, is_active=True)
        except ChatSession.DoesNotExist:
            logger.warning(f'Chat session {chat_session_id} not found or inactive')
            return {'success': False, 'error': 'Session not found'}
        
        # Check if session has enough messages to warrant summarization
        message_count = chat_session.messages.count()
        if message_count < message_threshold:
            logger.info(f'Session {chat_session_id} has only {message_count} messages, skipping summarization')
            return {'success': True, 'skipped': True, 'reason': 'Insufficient messages'}
        
        # Get recent messages for analysis
        recent_messages = ChatMessage.objects.filter(
            chat_session=chat_session
        ).order_by('created_at')
        
        # Build conversation text for summarization with content sanitization
        def sanitize_content(text):
            """Sanitize content to avoid safety filter triggers"""
            import re
            # Remove potentially sensitive patterns while preserving educational content
            sanitized = text
            
            # Replace specific medical terms with generic equivalents for safety
            medical_replacements = {
                r'\b(depression|anxiety|stress|mental health|suicide|self-harm)\b': 'academic challenges',
                r'\b(medication|drugs|pills)\b': 'study aids',
                r'\b(doctor|physician|medical)\b': 'academic advisor',
                r'\b(disease|illness|sick|patient)\b': 'academic concept',
                r'\b(pain|hurt|suffering)\b': 'difficulty',
            }
            
            for pattern, replacement in medical_replacements.items():
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            
            return sanitized
        
        conversation_text = []
        for msg in recent_messages:
            role = "Student" if msg.message_type == 'user' else "Tutor"
            sanitized_content = sanitize_content(msg.message_content)
            conversation_text.append(f"{role}: {sanitized_content}")
        
        conversation = "\n".join(conversation_text)
        
        # Create educational-focused summarization prompt
        summarization_prompt = f"""As an educational AI assistant, analyze this tutoring conversation to extract learning insights about the student. This is for educational personalization purposes only.

EDUCATIONAL CONTEXT: This is a conversation between a NEET (medical entrance exam) student and their AI tutor for academic improvement.

Extract key learning patterns in JSON format:

CONVERSATION SUMMARY:
{conversation[:2000]}  # Limit to first 2000 chars to avoid long prompts

Please return a JSON array with educational insights:
[
  {{
    "fact": "Academic insight about the student's learning",
    "type": "strength|weakness|preference|goal|habit", 
    "subjects": ["Physics", "Chemistry", "Biology"],
    "confidence": 0.8
  }}
]

Focus only on:
- Subject understanding levels
- Learning style preferences  
- Study approach patterns
- Academic goals and interests
- Knowledge gaps in specific topics

Maximum 3 insights. Return only valid JSON."""

        # Call LLM for summarization
        try:
            gemini_client = GeminiClient()
            if not gemini_client.is_available():
                logger.warning('Gemini client not available for memory summarization')
                return {'success': False, 'error': 'LLM not available'}
            
            llm_response = gemini_client.generate_response(summarization_prompt)
            logger.info(f'LLM summarization response: {llm_response[:200]}...')
            
            # Parse JSON response (handle markdown code blocks)
            try:
                # Clean the response - remove markdown code blocks if present
                cleaned_response = llm_response.strip()
                if cleaned_response.startswith('```json'):
                    # Remove opening ```json
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith('```'):
                    # Remove opening ```
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith('```'):
                    # Remove closing ```
                    cleaned_response = cleaned_response[:-3]
                
                cleaned_response = cleaned_response.strip()
                logger.info(f'Cleaned JSON response: {cleaned_response[:200]}...')

                # Attempt robust JSON extraction: sometimes LLM returns truncated or additional text.
                # Try to extract the first JSON array block from the cleaned response.
                facts = None
                try:
                    facts = json.loads(cleaned_response)
                except Exception:
                    # Attempt to extract JSON array with regex
                    import re
                    m = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned_response)
                    if m:
                        array_text = m.group(0)
                        try:
                            facts = json.loads(array_text)
                        except Exception as e:
                            logger.error(f'Regex-extracted JSON still invalid: {e}')
                            facts = None

                if not facts or not isinstance(facts, list):
                    raise ValueError("Response is not a list or could not be parsed")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f'Failed to parse LLM response as JSON: {e}')
                logger.error(f'Raw response: {llm_response}')

                # Check if it's a safety-related response - use fallback extraction
                if 'safety' in llm_response.lower() or 'cannot analyze' in llm_response.lower():
                    logger.warning('LLM response blocked by safety filters - using fallback extraction')
                    facts = _extract_fallback_insights(recent_messages, message_count)
                    if not facts:
                        return {'success': True, 'skipped': True, 'reason': 'Content blocked by safety filters, no fallback insights available'}
                else:
                    # As a last resort, persist a raw summary memory (low confidence) to avoid losing context
                    logger.warning('Persisting raw LLM response as low-confidence memory')
                    try:
                        student_profile = StudentProfile.objects.get(student_id=student_id)
                    except StudentProfile.DoesNotExist:
                        logger.error(f'StudentProfile not found for student_id: {student_id} when storing raw memory')
                        return {'success': False, 'error': f'Student profile not found for ID: {student_id}'}

                    ChatMemory.objects.create(
                        student=student_profile,
                        memory_type='long_term',
                        content={'raw_summary': llm_response},
                        source_session_id=chat_session_id,
                        key_tags=['llm_raw'],
                        confidence_score=0.25
                    )
                    return {'success': True, 'memories_created': 1, 'facts_extracted': 0, 'message_count': message_count, 'note': 'Stored raw LLM response as low-confidence memory'}
                
                return {'success': False, 'error': 'Invalid LLM response format'}
            
        except Exception as e:
            logger.error(f'LLM call failed: {e}')
            return {'success': False, 'error': f'LLM error: {str(e)}'}
        
        # Save extracted facts as memories
        memories_created = 0
        try:
            student_profile = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            logger.error(f'StudentProfile not found for student_id: {student_id}')
            return {'success': False, 'error': f'Student profile not found for ID: {student_id}'}
        
        for fact_data in facts:
            if not isinstance(fact_data, dict) or 'fact' not in fact_data:
                continue
            
            # Create or update memory
            memory_content = {
                'fact': fact_data.get('fact', ''),
                'type': fact_data.get('type', 'general'),
                'subjects': fact_data.get('subjects', []),
                'summary': fact_data.get('fact', ''),
                'source': 'conversation_analysis',
                'message_count': message_count
            }
            
            confidence = float(fact_data.get('confidence', 0.8))
            key_tags = fact_data.get('subjects', [])
            
            # Check for similar existing memory to avoid duplicates
            similar_memory = ChatMemory.objects.filter(
                student=student_profile,
                memory_type='long_term',
                content__fact__icontains=fact_data.get('fact', '')[:50]  # Check first 50 chars
            ).first()
            
            if similar_memory:
                # Update existing memory
                similar_memory.content = memory_content
                similar_memory.confidence_score = max(similar_memory.confidence_score, confidence)
                similar_memory.source_session_id = chat_session_id
                similar_memory.key_tags = list(set(similar_memory.key_tags + key_tags))
                similar_memory.save()
                logger.info(f'Updated existing memory: {fact_data.get("fact", "")[:50]}...')
            else:
                # Create new memory
                ChatMemory.objects.create(
                    student=student_profile,
                    memory_type='long_term',
                    content=memory_content,
                    source_session_id=chat_session_id,
                    key_tags=key_tags,
                    confidence_score=confidence
                )
                memories_created += 1
                logger.info(f'Created new memory: {fact_data.get("fact", "")[:50]}...')
        
        logger.info(f'Memory summarization completed: {memories_created} new memories created')
        return {
            'success': True,
            'memories_created': memories_created,
            'facts_extracted': len(facts),
            'message_count': message_count
        }
        
    except Exception:
        logger.exception('chat_memory_summarizer_task failed')
        raise


def _extract_fallback_insights(messages, message_count):
        """Extract basic insights without LLM when safety filters block content"""
        import re
        from collections import Counter
        
        try:
            # Analyze message patterns for basic insights
            user_messages = [msg.message_content for msg in messages if msg.message_type == 'user']
            all_text = ' '.join(user_messages).lower()
            
            # Subject detection
            subjects = []
            if any(word in all_text for word in ['physics', 'mechanics', 'thermodynamics', 'waves']):
                subjects.append('Physics')
            if any(word in all_text for word in ['chemistry', 'organic', 'inorganic', 'reactions']):
                subjects.append('Chemistry')  
            if any(word in all_text for word in ['biology', 'botany', 'zoology', 'genetics']):
                subjects.append('Biology')
            
            facts = []
            
            # Basic engagement pattern
            if message_count >= 10:
                facts.append({
                    "fact": f"Student engaged in extended learning session with {message_count} interactions",
                    "type": "habit",
                    "subjects": subjects or ["General"],
                    "confidence": 0.7
                })
            
            # Subject focus
            if subjects:
                facts.append({
                    "fact": f"Student showed interest in {', '.join(subjects)} topics",
                    "type": "preference", 
                    "subjects": subjects,
                    "confidence": 0.6
                })
            
            return facts[:2]  # Maximum 2 fallback insights
            
        except Exception as e:
            logger.error(f'Fallback insight extraction failed: {e}')
            return []

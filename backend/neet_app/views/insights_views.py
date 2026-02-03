"""
Student Performance Insights Views
Provides topic-wise performance analysis, strengths, weaknesses, and study recommendations.
"""

from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg, F
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
from collections import defaultdict
import logging
import google.generativeai as genai
from django.conf import settings
import os

from ..models import StudentProfile, TestSession, TestAnswer, Question, Topic, StudentInsight

logger = logging.getLogger(__name__)

# Insights cache moved to database-backed storage; file-cache helpers removed

def is_celery_worker_available():
    """
    Check if Celery workers are available and ready to process tasks.
    Uses very short timeouts to avoid blocking.
    
    Returns:
        bool: True if workers are available, False otherwise
    """
    try:
        from celery import current_app
        import socket
        
        # First, do a quick socket check to the Redis broker
        try:
            # Parse Redis URL to get host and port
            broker_url = current_app.conf.broker_url
            if 'redis://' in broker_url:
                # Quick socket test with minimal timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)  # 100ms timeout
                result = sock.connect_ex(('127.0.0.1', 6379))
                sock.close()
                
                if result != 0:
                    print(f"❌ Error connecting to broker while checking workers: Connection refused")
                    print("❌ Celery broker appears unreachable - tasks cannot be enqueued or processed")
                    return False
            
            print("✅ Celery broker is reachable")
        except Exception as broker_e:
            print(f"❌ Error connecting to broker while checking workers: {str(broker_e)}")
            print("❌ Celery broker appears unreachable - tasks cannot be enqueued or processed")
            return False
        
        # If broker is reachable, do a quick check for active workers
        try:
            inspect = current_app.control.inspect(timeout=0.5)  # 500ms timeout
            active_workers = inspect.active()
            if active_workers:
                print(f"✅ Celery workers detected: {list(active_workers.keys())}")
                return True
            else:
                print(f"⚠️ No active Celery workers found")
                return False
        except Exception as inspect_e:
            print(f"❌ Error inspecting workers: {str(inspect_e)}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Celery workers: {str(e)}")
        return False

# File-based cache helpers removed (use DB-backed `save_insights_to_database` / `load_insights_from_database`)

def save_insights_to_database(student_id, insights_data, test_session_id=None):
    """Save insights data to the database."""
    try:
        # Get the student profile
        student = StudentProfile.objects.get(student_id=student_id)
        
        # Get test session if provided
        test_session = None
        if test_session_id:
            try:
                test_session = TestSession.objects.get(id=test_session_id)
            except TestSession.DoesNotExist:
                print(f"⚠️ Test session {test_session_id} not found, saving without session link")
        
        # Extract data from the insights_data structure
        data = insights_data.get('data', insights_data)
        
        # Create new StudentInsight record
        insight = StudentInsight.objects.create(
            student=student,
            test_session=test_session,
            strength_topics=data.get('strength_topics', []),
            weak_topics=data.get('weak_topics', []),
            improvement_topics=data.get('improvement_topics', []),
            unattempted_topics=data.get('unattempted_topics', []),
            # Note: last_test_topics and llm_last_test_feedback removed by design
            llm_strengths=data.get('llm_insights', {}).get('strengths', {}),
            llm_weaknesses=data.get('llm_insights', {}).get('weaknesses', {}),
            llm_study_plan=data.get('llm_insights', {}).get('study_plan', {}),
            thresholds_used=data.get('thresholds_used', {}),
            summary=data.get('summary', {}),
            insight_type='overall'
        )
        
        print(f"💾 Insights saved to database for student {student_id} (ID: {insight.id})")
        return True
    except StudentProfile.DoesNotExist:
        print(f"❌ Student {student_id} not found")
        logger.error(f"Student {student_id} not found when saving insights")
        return False
    except Exception as e:
        print(f"❌ Failed to save insights to database for student {student_id}: {e}")
        logger.error(f"Failed to save insights to database for student {student_id}: {e}")
        return False

def load_insights_from_database(student_id):
    """Load the most recent insights data from the database."""
    try:
        # Get the most recent insight for this student
        insight = StudentInsight.objects.filter(student_id=student_id).order_by('-created_at').first()
        
        if not insight:
            print(f"📂 No insights found in database for student {student_id}")
            return None
        
        # Reconstruct the data structure to match the original format
        insights_data = {
            'status': 'success',
            'data': {
                'strength_topics': insight.strength_topics,
                'weak_topics': insight.weak_topics,
                'improvement_topics': insight.improvement_topics,
                'unattempted_topics': insight.unattempted_topics,
                # Note: last_test_topics and last_test_feedback intentionally omitted
                'llm_insights': {
                    'strengths': insight.llm_strengths,
                    'weaknesses': insight.llm_weaknesses,
                    'study_plan': insight.llm_study_plan
                },
                'thresholds_used': insight.thresholds_used,
                'summary': insight.summary,
                'cached': True
            }
        }
        
        print(f"📂 Insights loaded from database for student {student_id} (created: {insight.created_at})")
        return insights_data
    except Exception as e:
        print(f"❌ Failed to load insights from database for student {student_id}: {e}")
        logger.error(f"Failed to load insights from database for student {student_id}: {e}")
        return None

# File-based cache helpers removed — use database-backed caching via
# `save_insights_to_database` and `load_insights_from_database` instead.

# Configure Gemini API
GEMINI_API_KEYS = getattr(settings, 'GEMINI_API_KEYS', [])
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))

# Use multiple keys if available, fallback to single key
AVAILABLE_API_KEYS = GEMINI_API_KEYS if GEMINI_API_KEYS else ([GEMINI_API_KEY] if GEMINI_API_KEY else [])

if AVAILABLE_API_KEYS:
    # Configure with the first available key (we'll rotate in the function)
    genai.configure(api_key=AVAILABLE_API_KEYS[0])

# LLM Prompts for different insight types
INSIGHT_PROMPTS = {
    'strengths': """
Act as a highly personalized NEET and JEE exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. Use the topic metadata: if a topic's `subject` is "Math" treat it with JEE framing (math problem-solving strategies and higher quantitative standards); for all other subjects use NEET framing.
For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are an encouraging NEET exam tutor. A student has shown excellent performance in the following topics. 
Provide exactly 2 encouraging points in a supportive teacher tone that:
1. Praise their mastery and quick thinking
2. Motivate them to maintain this excellence
Keep each point to 1-2 sentences. Be specific about their achievements.

Important — use the topic metadata and the `questions` array included in each topic (each question has: question_id, options, correct_answer, selected_answer, is_correct, time_taken). Analyze question-by-question to generate candidate insights, rank them by impact and actionability, and return exactly 2 actionable insights ordered most-actionable-first.

Topics data: {data}
""",
    
    'weaknesses': """
Act as a highly personalized NEET and JEE exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. Use the topic metadata: if a topic's `subject` is "Math" treat it with JEE framing (math problem-solving strategies and higher quantitative standards); for all other subjects use NEET framing.
For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are a supportive NEET exam tutor. A student needs improvement in the following topics.
Provide exactly 2 constructive points in a positive, encouraging teacher tone that:
1. Identify areas needing focused revision without discouraging
2. Give a motivational push with specific improvement suggestions
Keep each point to 1-2 sentences. Focus on growth, not shortcomings.

Important — use the topic metadata and the `questions` array included in each topic (each question has: question_id, options, correct_answer, selected_answer, is_correct, time_taken). Analyze question-by-question to generate candidate insights, rank them by impact and actionability, and return exactly 2 actionable insights ordered most-actionable-first.

Topics data: {data}
"""
}
# Thresholds removed: classification no longer depends on configurable thresholds.
# Previous dynamic thresholds have been removed to avoid gating topics.
# Note: 'study_plan' prompt removed - now uses misconception-based service in study_plan_service.py

def generate_llm_insights(insight_type, data):
    """
    Generate LLM-powered insights using Gemini API.
    
    Args:
        insight_type: Type of insight ('strengths', 'weaknesses', 'study_plan')
        data: Topic data to analyze
        
    Returns:
        dict: LLM-generated insights or fallback message
    """
    try:
        # Build prompt
        if not data:
            print(f"⚠️ No data available for {insight_type} analysis")
            return {
                'status': 'info',
                'message': 'No data available for analysis',
                'insights': ['No test data available yet', 'Take some tests to get personalized insights']
            }

        prompt_template = INSIGHT_PROMPTS.get(insight_type, INSIGHT_PROMPTS['strengths'])
        # If DEBUG is True, print the exact payload being sent to the LLM for easier inspection.
        try:
            if getattr(settings, 'DEBUG', False):
                print(f"🔎 LLM_PAYLOAD ({insight_type}):\n{json.dumps(data, indent=2)[:20000]}")
        except Exception:
            # Non-fatal: do not prevent LLM generation if logging fails
            pass

        prompt = prompt_template.format(data=json.dumps(data, indent=2))

        # Prefer centralized GeminiClient which uses model 'gemini-2.5-flash' and handles key rotation/safety
        try:
            from .services.ai.gemini_client import GeminiClient
        except Exception:
            # Fallback import path if module resolution differs
            from neet_app.services.ai.gemini_client import GeminiClient

        client = GeminiClient()

        if not client.is_available():
            print(f"❌ Gemini client not available for {insight_type}")
            return {
                'status': 'warning',
                'message': 'Gemini client not available',
                'insights': ['AI unavailable: configure GEMINI_API_KEYS', 'Using basic analysis for now']
            }

        print(f"🚀 Generating LLM insights for {insight_type} using model {client.model_name}")
        llm_response = client.generate_response(prompt)

        insights_text = (llm_response or '').strip()
        print(f"📖 Raw response: {insights_text[:200]}...")

        # Parse response into individual points (bullets or numbered lines)
        insights = []
        lines = insights_text.split('\n')
        
        # First pass: try to extract numbered or bulleted points
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if line starts with number, bullet, dash, or asterisk
            if line[0].isdigit() or line.startswith('•') or line.startswith('-') or line.startswith('*'):
                clean_line = line.lstrip('0123456789.• -*').strip()
                if clean_line and len(clean_line) > 15:  # At least 15 chars
                    insights.append(clean_line)
        
        # Second pass: If no structured points found, extract meaningful sentences
        if len(insights) < 2 and insights_text:
            # Remove greetings and conversational fluff
            text_to_parse = insights_text
            # Remove common greeting patterns
            greeting_patterns = [
                r'Hello.*?!',
                r'Hi.*?!',
                r'Great to connect.*?!',
                r"Let's work together.*?!",
                r"I've carefully reviewed.*?\.",
                r"I see a lot of potential.*?\."
            ]
            import re
            for pattern in greeting_patterns:
                text_to_parse = re.sub(pattern, '', text_to_parse, flags=re.IGNORECASE)
            
            # Split into sentences
            sentences = [s.strip() for s in text_to_parse.replace('\n', ' ').split('.') if s.strip()]
            # Filter out very short or generic sentences
            meaningful_sentences = [s + '.' for s in sentences if len(s) > 20 and not any(x in s.lower() for x in ['hello', 'great to', 'let\'s work'])]
            insights.extend(meaningful_sentences[:2])

        if not insights:
            # Final fallback messages
            fallback_map = {
                'strengths': ["No AI strengths available yet."],
                'weaknesses': ["No AI weaknesses available yet."],
                'study_plan': ["No AI study plan available yet."]
            }
            return {
                'status': 'info',
                'message': 'No insights parsed from LLM response',
                'insights': fallback_map.get(insight_type, ["No AI insights available."])
            }

        return {
            'status': 'success',
            'message': 'AI insights generated successfully',
            'insights': insights[:2]
        }

    except Exception as e:
        print(f"❌ Error generating LLM insights for {insight_type}: {str(e)}")
        logger.error(f"Error generating LLM insights for {insight_type}: {str(e)}")

        fallback_insights = {
            'strengths': [
                "I couldn’t identify your strong areas yet, but with consistent practice and effort, your strengths will surely become visible soon."
            ],
            'weaknesses': [
                "No clear weaknesses are visible from this data, but continued practice and deeper learning will help uncover improvement opportunities ahead."
            ],
            'study_plan': [
                "Currently, there isn’t enough data to design a study plan, but attempting more tests will allow personalized guidance soon."
            ],
            # 'last_test_feedback' fallback removed (feature deprecated)
            'no_data': [
                "There’s no test data available yet, but once you take your first test, personalized strengths and weaknesses will be generated."
            ]
        }

        return {
            'status': 'error',
            'message': f'AI generation failed: {str(e)}',
            'insights': fallback_insights.get(insight_type, fallback_insights['strengths'])
        }

def calculate_topic_metrics(student_id, session_ids=None):
    """
    Calculate per-topic metrics for a student.
    
    Args:
        student_id: Student ID to analyze
        session_ids: Optional list of specific session IDs to analyze
        
    Returns:
        dict: Topic metrics with accuracy, avg_time, attempted, correct, etc.
    """
    try:
        # Build base query for test answers
        base_query = TestAnswer.objects.filter(
            session__student_id=student_id
        ).select_related('question__topic', 'session')
        
        # Filter by specific sessions if provided
        if session_ids:
            base_query = base_query.filter(session_id__in=session_ids)
        
        # Get all test answers with topic information
        test_answers = base_query.all()
        
        if not test_answers:
            return {}
        
        # Group answers by topic
        # Include question-level details to send to LLM (question text, options, correct answer, selected answer)
        MAX_QUESTIONS_PER_TOPIC = 20
        topic_data = defaultdict(lambda: {
            'attempted': 0,
            'correct': 0,
            'total_time': 0,
            'topic_name': '',
            'subject': '',
            'chapter': '',
            'total_questions': 0,
            'questions': []  # list of question-level dicts
        })
        
        total_attempted = 0
        total_time = 0
        
        for answer in test_answers:
            topic = answer.question.topic
            topic_key = f"{topic.id}_{topic.name}"
            
            # Initialize topic info
            if not topic_data[topic_key]['topic_name']:
                topic_data[topic_key]['topic_name'] = topic.name
                topic_data[topic_key]['subject'] = topic.subject
                topic_data[topic_key]['chapter'] = topic.chapter
            
            # Count attempted (any answer selected)
            if answer.selected_answer is not None:
                topic_data[topic_key]['attempted'] += 1
                total_attempted += 1
                
                # Add time taken (default to 0 if None)
                time_taken = answer.time_taken or 0
                topic_data[topic_key]['total_time'] += time_taken
                total_time += time_taken
                
                # Count correct answers
                if answer.is_correct:
                    topic_data[topic_key]['correct'] += 1

                # Append question-level details (limit per topic)
                try:
                    q = answer.question
                    # Prepare options dict
                    options = {
                        'A': q.option_a,
                        'B': q.option_b,
                        'C': q.option_c,
                        'D': q.option_d,
                    }
                    # Include only necessary fields to keep prompts compact
                    question_entry = {
                        'question_id': q.id,
                        'question': q.question,
                        'options': options,
                        'correct_answer': (q.correct_answer if q.correct_answer else None),
                        'selected_answer': (answer.selected_answer if answer.selected_answer else None),
                        'is_correct': True if answer.is_correct is True else (False if answer.is_correct is False else None),
                        'time_taken': time_taken,
                    }

                    if len(topic_data[topic_key]['questions']) < MAX_QUESTIONS_PER_TOPIC:
                        topic_data[topic_key]['questions'].append(question_entry)
                except Exception:
                    # Non-fatal: if any question fields missing or error occurs, skip question details
                    pass
        
        # Get total questions per topic for unattempted calculation
        from django.db.models import Count
        topic_question_counts = Question.objects.values('topic__id', 'topic__name').annotate(
            total_questions=Count('id')
        )
        
        # Map topic question counts
        topic_totals = {}
        for item in topic_question_counts:
            topic_key = f"{item['topic__id']}_{item['topic__name']}"
            topic_totals[topic_key] = item['total_questions']
        
        # Calculate metrics for each topic
        topic_metrics = {}
        overall_avg_time = total_time / total_attempted if total_attempted > 0 else 0
        
        for topic_key, data in topic_data.items():
            if data['attempted'] > 0:
                accuracy = (data['correct'] / data['attempted']) * 100
                avg_time = data['total_time'] / data['attempted']
                total_questions = topic_totals.get(topic_key, data['attempted'])
                unattempted = max(0, total_questions - data['attempted'])
                
                topic_metrics[topic_key] = {
                    'topic': data['topic_name'],
                    'subject': data['subject'],
                    'chapter': data['chapter'],
                    'accuracy': round(accuracy, 2),
                    'avg_time_sec': round(avg_time, 2),
                    'attempted': data['attempted'],
                    'correct': data['correct'],
                    'total_time': data['total_time'],
                    'total_questions': total_questions,
                    'unattempted': unattempted
                    ,
                    # Include question-level samples so downstream LLM prompts can analyze specific questions
                    'questions': data.get('questions', [])
                }
        
        return {
            'topics': topic_metrics,
            'overall_avg_time': overall_avg_time,
            'total_attempted': total_attempted
        }
        
    except Exception as e:
        logger.error(f"Error calculating topic metrics for student {student_id}: {str(e)}")
        return {}

def classify_topics(topic_metrics, overall_avg_time, thresholds):
    """
    Classify topics into strengths, weaknesses, and areas for improvement.
    
    Args:
        topic_metrics: Dict of topic metrics from calculate_topic_metrics
        overall_avg_time: Overall average time per question
        thresholds: Dict of classification thresholds
        
    Returns:
        dict: Classified topics (strengths, weaknesses, improvements)
    """
    """
    New classification logic (threshold-free):
    - Do not skip topics based on attempt counts or configured thresholds.
    - Classify topics relative to the student's mean accuracy across all topics:
      * Strengths: accuracy > mean + 10
      * Weaknesses: accuracy < mean - 10
      * Improvements: everything else

    This removes the gating behavior of configured thresholds so all attempted
    topics are considered for LLM analysis and saved insights.
    """

    strengths = []
    weaknesses = []
    improvements = []

    # Build a simple list of accuracies to compute mean
    accuracies = []
    for topic_key, metrics in topic_metrics.items():
        # Only include topics that have been attempted at least once
        if metrics.get('attempted', 0) >= 1:
            accuracies.append(metrics.get('accuracy', 0))

    if not accuracies:
        # Nothing to classify
        return {
            'strength_topics': [],
            'weak_topics': [],
            'improvement_topics': []
        }

    mean_accuracy = sum(accuracies) / len(accuracies)
    upper_cut = mean_accuracy + 10.0
    lower_cut = mean_accuracy - 10.0

    for topic_key, metrics in topic_metrics.items():
        # Include all topics that have at least one attempt
        if metrics.get('attempted', 0) < 1:
            # Skip topics with zero attempts entirely
            continue

        accuracy = metrics.get('accuracy', 0)

        entry = {
            'topic': metrics['topic'],
            'accuracy': metrics.get('accuracy', 0),
            'avg_time_sec': metrics.get('avg_time_sec', 0),
            'subject': metrics.get('subject', ''),
            'chapter': metrics.get('chapter', ''),
            'questions': metrics.get('questions', [])
        }

        if accuracy > upper_cut:
            strengths.append(entry)
        elif accuracy < lower_cut:
            weaknesses.append(entry)
        else:
            improvements.append(entry)

    return {
        'strength_topics': strengths,
        'weak_topics': weaknesses,
        'improvement_topics': improvements
    }

def get_unattempted_topics(topic_metrics, unattempted_threshold=5):
    """
    Identify topics with high number of unattempted questions.
    
    Args:
        topic_metrics: Dict of topic metrics from calculate_topic_metrics
        unattempted_threshold: Minimum unattempted questions to be considered
        
    Returns:
        list: Topics with high unattempted counts
    """
    unattempted_topics = []
    
    for topic_key, metrics in topic_metrics.items():
        if metrics.get('unattempted', 0) >= unattempted_threshold:
            unattempted_topics.append({
                'topic': metrics['topic'],
                'subject': metrics['subject'],
                'chapter': metrics['chapter'],
                'unattempted': metrics['unattempted'],
                'total_questions': metrics['total_questions'],
                'attempted': metrics['attempted'],
                'unattempted_percentage': round((metrics['unattempted'] / metrics['total_questions']) * 100, 2) if metrics['total_questions'] > 0 else 0
            })
    
    # Sort by unattempted count (descending)
    unattempted_topics.sort(key=lambda x: x['unattempted'], reverse=True)
    
    return unattempted_topics

# Note: last-test topic metric removed — functionality intentionally omitted.


def is_valid_insight(insight):
    """
    Check if an insight is valid (not a fallback/placeholder message).
    
    Args:
        insight: String to validate
        
    Returns:
        bool: True if valid, False if fallback/placeholder
    """
    if not insight or not isinstance(insight, str):
        return False
    
    insight_lower = insight.lower().strip()
    
    # Filter out insights that are too short
    if len(insight_lower) < 10:
        return False
    
    # Fallback phrases to exclude (case-insensitive)
    fallback_phrases = [
        'no data',
        'insufficient',
        'insufficient data',
        'continue practicing',
        'additional analysis needed',
        'no insights',
        'not available',
        'not enough',
        'not sufficient',
        'no test data',
        'complete more',
        'for better insights',
        'no analysis',
        'unavailable',
        'take more tests',
        'attempt more',
    ]
    
    # Check if any fallback phrase is present
    for phrase in fallback_phrases:
        if phrase in insight_lower:
            return False
    
    return True


# Note: zone-based last-test feedback removed — function intentionally omitted.

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def get_student_insights(request):
    """
    Get comprehensive insights for the authenticated student including strengths, weaknesses, 
    areas for improvement, and last test feedback.
    
    First checks for cached insights file, if not found generates new insights.
    
    POST/GET Body (optional for custom thresholds):
    {
        "strength_accuracy": 80.0,     // Optional: Custom threshold for strength
        "weakness_accuracy": 60.0,     // Optional: Custom threshold for weakness  
        "time_multiplier": 1.2,        // Optional: Custom time multiplier
        "min_attempts": 3,             // Optional: Minimum attempts for analysis
        "force_regenerate": false      // Optional: Force regenerate even if cache exists
    }
    
    Returns:
    {
        "status": "success",
        "data": {
            "strength_topics": [...],
            "weak_topics": [...], 
            "improvement_topics": [...],
            "last_test_topics": [...],
            "thresholds_used": {...},
            "summary": {...},
            "llm_insights": {...},         // LLM-generated insights
            "cached": true/false           // Whether data was loaded from cache
        }
    }
    """
    try:
        # Get the authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        # Parse request data
        if request.method == 'POST' and request.body:
            data = json.loads(request.body)
        elif request.method == 'GET':
            data = request.GET.dict()
        else:
            data = {}
        
        # Remove student_id from data if provided (we use authenticated user's ID)
        data.pop('student_id', None)
        force_regenerate = data.pop('force_regenerate', False)
        
        # Verify student exists
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Student with ID {student_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Try to load from database first (unless force_regenerate is True)
        if not force_regenerate:
            cached_insights = load_insights_from_database(student_id)
            if cached_insights:
                # Add cached flag to the response
                cached_insights['cached'] = True
                return Response(cached_insights)

        # If client requests async generation, enqueue Celery task and return task id immediately
        async_flag = False
        if isinstance(data, dict):
            async_flag = bool(data.pop('async', False) or data.pop('async_generate', False))
        if async_flag:
            try:
                from .tasks import generate_insights_task
                
                # Check if Celery workers are available before enqueueing
                if not is_celery_worker_available():
                    print(f"⚠️ No active Celery workers detected, processing insights synchronously for student {student_id}")
                    logger.warning('No active Celery workers found - falling back to synchronous generation')
                    # Fall back to synchronous generation when no workers are available
                    # Continue to the synchronous generation code below
                else:
                    print(f"✅ Celery workers available, enqueueing insights task for student {student_id}")
                    task = generate_insights_task.delay(student_id, data, force_regenerate)
                    return Response({'status': 'queued', 'task_id': task.id}, status=202)
                    
            except Exception as e:
                logger.exception('Failed to enqueue generate_insights_task - falling back to synchronous generation')
                print(f"⚠️ Celery unavailable, processing insights synchronously for student {student_id}: {str(e)}")
                # Fall back to synchronous generation when Celery is unavailable
                # Continue to the synchronous generation code below instead of returning error
        
        # Generate new insights if cache not found or force_regenerate is True
        print(f"🔄 Generating new insights for student {student_id}")
        
        # Thresholds concept removed; proceed without configurable thresholds
        thresholds = {}
        
        # Calculate overall metrics (all tests)
        all_metrics = calculate_topic_metrics(student_id)
        
        if not all_metrics or 'topics' not in all_metrics:
            empty_response = {
                'status': 'success',
                'data': {
                    'strength_topics': [],
                    'weak_topics': [],
                    'improvement_topics': [],
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
            # Save empty response to database
            save_insights_to_database(student_id, empty_response)
            return Response(empty_response)
        
        # Classify topics based on all test data
        classification = classify_topics(
            all_metrics['topics'], 
            all_metrics['overall_avg_time'], 
            thresholds
        )
        
        # Check if classification has any topics - if not, use all topics with lower thresholds
        if not classification['strength_topics'] and not classification['weak_topics'] and not classification['improvement_topics']:
            print(f"⚠️ No topics passed classification thresholds, using all topics for analysis")
            # Use all available topics for analysis with relaxed thresholds
            all_topics_list = list(all_metrics['topics'].values())
            if all_topics_list:
                # Split topics based on accuracy alone (no min_attempts filter)
                classification['strength_topics'] = [t for t in all_topics_list if t['accuracy'] >= 70]
                classification['weak_topics'] = [t for t in all_topics_list if t['accuracy'] < 50]
                classification['improvement_topics'] = [t for t in all_topics_list if 50 <= t['accuracy'] < 70]
        
        # Generate LLM insights for each category
        llm_insights = {}
        
        # Filter questions by correctness before sending to LLM
        # Strengths: only correct questions (is_correct=True)
        strength_topics_filtered = []
        for topic in classification['strength_topics']:
            topic_copy = topic.copy()
            topic_copy['questions'] = [q for q in topic.get('questions', []) if q.get('is_correct') is True]
            strength_topics_filtered.append(topic_copy)
        
        # Weaknesses: only wrong questions (is_correct=False)
        weak_topics_filtered = []
        for topic in classification['weak_topics']:
            topic_copy = topic.copy()
            topic_copy['questions'] = [q for q in topic.get('questions', []) if q.get('is_correct') is False]
            weak_topics_filtered.append(topic_copy)
        
        # Generate insights for strengths (even if empty, still call to get fallback)
        if strength_topics_filtered:
            llm_insights['strengths'] = generate_llm_insights('strengths', strength_topics_filtered)
        else:
            llm_insights['strengths'] = {
                'status': 'info',
                'message': 'No strength topics identified yet',
                'insights': ['Keep practicing to identify your strong areas!']
            }
        
        # Generate insights for weaknesses (even if empty, still call to get fallback)
        if weak_topics_filtered:
            llm_insights['weaknesses'] = generate_llm_insights('weaknesses', weak_topics_filtered)
        else:
            llm_insights['weaknesses'] = {
                'status': 'info',
                'message': 'No weak topics identified yet',
                'insights': ['Continue practicing to identify areas for improvement!']
            }
        
        # Generate study plan insights using new misconception-based approach
        from neet_app.services.study_plan_service import generate_study_plan_from_misconceptions
        study_plan_result = generate_study_plan_from_misconceptions(student_id, max_tests=5)
        
        # Format study plan result to match expected structure
        if study_plan_result['status'] == 'success':
            llm_insights['study_plan'] = {
                'status': 'success',
                'message': study_plan_result.get('analysis_summary', ''),
                'insights': [
                    f"{rec['rank']}. {rec['title']}: {rec['reasoning'][:100]}..."
                    for rec in study_plan_result.get('recommendations', [])[:5]
                ],
                'recommendations': study_plan_result.get('recommendations', [])
            }
        elif study_plan_result['status'] == 'insufficient_data':
            llm_insights['study_plan'] = {
                'status': 'info',
                'message': study_plan_result.get('message', 'Not enough data for study plan'),
                'insights': ['Complete more tests to get personalized study recommendations based on your misconceptions.']
            }
        else:
            llm_insights['study_plan'] = {
                'status': 'warning',
                'message': 'Study plan generation temporarily unavailable',
                'insights': ['Please try again later or contact support if the issue persists.']
            }
        
        # Last-test feedback/metrics removed — not included in insights
        
        # Prepare summary
        total_topics = len(all_metrics['topics'])
        total_tests = TestSession.objects.filter(
            student_id=student_id, 
            is_completed=True
        ).count()
        
        # Get the latest test session ID for tracking
        latest_session = TestSession.objects.filter(
            student_id=student_id, 
            is_completed=True
        ).order_by('-end_time').first()
        latest_session_id = latest_session.id if latest_session else None
        
        # Calculate unattempted topics for summary
        unattempted_topics = get_unattempted_topics(all_metrics['topics'])
        
        summary = {
            'total_topics_analyzed': total_topics,
            'total_tests_taken': total_tests,
            'strengths_count': len(classification['strength_topics']),
            'weaknesses_count': len(classification['weak_topics']),
            'improvements_count': len(classification['improvement_topics']),
            'unattempted_topics_count': len(unattempted_topics),
            'overall_avg_time': round(all_metrics['overall_avg_time'], 2),
            'last_session_id': latest_session_id  # Add this for tracking
        }
        
        response_data = {
            'status': 'success',
            'data': {
                **classification,
                'unattempted_topics': unattempted_topics,
                'llm_insights': llm_insights,
                'summary': summary,
                'cached': False
            }
        }
        
        # Save the generated insights to database
        save_insights_to_database(student_id, response_data, latest_session_id)
        
        return Response(response_data)
        
    except json.JSONDecodeError:
        return Response({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in get_student_insights: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_topic_details(request):
    """
    Get detailed analysis for specific topics for the authenticated student.
    
    POST Body:
    {
        "topic_names": ["Kinematics", "Thermodynamics"],  // Optional: specific topics
        "include_questions": true                           // Optional: include question-level data
    }
    
    Returns detailed metrics for requested topics including question-level breakdown.
    """
    try:
        # Get the authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        data = json.loads(request.body) if request.body else {}
        topic_names = data.get('topic_names', [])
        include_questions = data.get('include_questions', False)
        
        # Calculate metrics
        all_metrics = calculate_topic_metrics(student_id)
        
        if not all_metrics or 'topics' not in all_metrics:
            return Response({
                'status': 'success',
                'data': {'topics': []}
            })
        
        # Filter by requested topics if specified
        filtered_topics = {}
        for topic_key, metrics in all_metrics['topics'].items():
            if not topic_names or metrics['topic'] in topic_names:
                topic_data = metrics.copy()
                
                # Add question-level details if requested
                if include_questions:
                    # Get question-level data for this topic
                    question_data = TestAnswer.objects.filter(
                        session__student_id=student_id,
                        question__topic__name=metrics['topic']
                    ).select_related('question').values(
                        'question__id',
                        'question__question',
                        'selected_answer',
                        'is_correct',
                        'time_taken',
                        'answered_at'
                    )
                    
                    topic_data['questions'] = list(question_data)
                
                filtered_topics[topic_key] = topic_data
        
        return Response({
            'status': 'success',
            'data': {
                'topics': filtered_topics,
                'overall_avg_time': all_metrics['overall_avg_time']
            }
        })
        
    except json.JSONDecodeError:
        return Response({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in get_topic_details: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_insights_cache(request):
    """
    Get cached insights data directly from the database for the authenticated student.
    This endpoint reads the cached insights from the database and returns the data without regeneration.
    
    Returns:
    {
        "status": "success",
        "data": {...},           // Cached insights data
        "cached": true,
        "cache_info": {
            "record_exists": true,
            "created_at": "2025-08-13T12:40:00Z",
            "test_session_id": 123
        }
    }
    """
    try:
        # Get the authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        print(f"📂 CACHE_ENDPOINT: Loading cached insights for student {student_id}")
        
        # Try to load from database
        cached_insights = load_insights_from_database(student_id)
        
        if cached_insights:
            # Get the actual record for cache info
            insight_record = StudentInsight.objects.filter(student_id=student_id).order_by('-created_at').first()
            cache_info = {
                'record_exists': True,
                'created_at': insight_record.created_at.isoformat() if insight_record else None,
                'test_session_id': insight_record.test_session.id if insight_record and insight_record.test_session else None
            }
            
            # Add cache info to response
            response_data = {
                'status': 'success',
                'data': cached_insights.get('data', cached_insights),  # Handle nested data structure
                'cached': True,
                'cache_info': cache_info
            }
            
            print(f"📂 CACHE_ENDPOINT: Successfully loaded cached insights for student {student_id}")
            return Response(response_data)
        else:
            # No cache found - return empty structure
            print(f"📂 CACHE_ENDPOINT: No cached insights found for student {student_id}")
            return Response({
                'status': 'success',
                'data': {
                    'strength_topics': [],
                    'weak_topics': [],
                    'improvement_topics': [],
                    'last_test_topics': [],
                    'unattempted_topics': [],
                    'llm_insights': {
                        'strengths': {
                            'status': 'info',
                            'message': 'No cached insights available',
                            'insights': ['Take some tests to get AI analysis of your strengths!']
                        },
                        'weaknesses': {
                            'status': 'info', 
                            'message': 'No cached insights available',
                            'insights': ['Take some tests to get AI analysis of your weaknesses!']
                        },
                        'study_plan': {
                            'status': 'info',
                            'message': 'No cached insights available', 
                            'insights': ['Take some tests to get AI-generated study plans!']
                        },
                        # last_test_feedback intentionally removed from cache response
                    },
                    'summary': {
                        'total_topics_analyzed': 0,
                        'total_tests_taken': 0,
                        'strengths_count': 0,
                        'weaknesses_count': 0,
                        'improvements_count': 0,
                        'unattempted_topics_count': 0
                    }
                },
                'cached': False,
                'cache_info': {
                    'record_exists': False,
                    'created_at': None,
                    'test_session_id': None
                }
            })
        
    except Exception as e:
        logger.error(f"Error in get_insights_cache: {str(e)}")
        print(f"❌ CACHE_ENDPOINT: Error loading cached insights: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_insights_history(request):
    """
    Get historical insights for the authenticated student.
    
    Query Parameters:
    - limit: Number of records to return (default: 10)
    - test_session_id: Filter by specific test session (optional)
    
    Returns:
    {
        "status": "success",
        "data": {
            "insights": [...],    // List of historical insights
            "total_count": 25,    // Total number of insights available
            "page_info": {...}    // Pagination info
        }
    }
    """
    try:
        # Get the authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        # Get query parameters
        limit = int(request.GET.get('limit', 10))
        test_session_id = request.GET.get('test_session_id')
        
        # Build query
        query = StudentInsight.objects.filter(student_id=student_id)
        
        if test_session_id:
            query = query.filter(test_session_id=test_session_id)
        
        # Get total count
        total_count = query.count()
        
        # Get limited results
        insights = query.order_by('-created_at')[:limit]
        
        # Format results
        insights_data = []
        for insight in insights:
            insights_data.append({
                'id': insight.id,
                'created_at': insight.created_at.isoformat(),
                'test_session_id': insight.test_session.id if insight.test_session else None,
                'insight_type': insight.insight_type,
                'summary': insight.summary,
                'strengths_count': len(insight.strength_topics),
                'weaknesses_count': len(insight.weak_topics),
                'improvements_count': len(insight.improvement_topics),
                # Include full data if needed
                'data': {
                    'strength_topics': insight.strength_topics,
                    'weak_topics': insight.weak_topics,
                    'improvement_topics': insight.improvement_topics,
                    'unattempted_topics': insight.unattempted_topics,
                    'llm_insights': {
                        'strengths': insight.llm_strengths,
                        'weaknesses': insight.llm_weaknesses,
                        'study_plan': insight.llm_study_plan
                    },
                    'thresholds_used': insight.thresholds_used
                }
            })
        
        return Response({
            'status': 'success',
            'data': {
                'insights': insights_data,
                'total_count': total_count,
                'page_info': {
                    'limit': limit,
                    'returned_count': len(insights_data),
                    'has_more': total_count > limit
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_insights_history: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_topic_history_by_test(student_id, include='correct', max_tests=None):
    """
    Get topic-wise performance history grouped by test.
    
    Args:
        student_id: Student ID to analyze
        include: 'correct' for strengths (only correct answers) or 'wrong' for weaknesses (only wrong answers)
        max_tests: Maximum number of tests to include (default: all tests)
        
    Returns:
        list: Topics with metadata and questions grouped by test
        [
            {
                "topic": "Kinematics",
                "subject": "Physics",
                "chapter": "Motion",
                "accuracy": 75.0,
                "avg_time_sec": 42.5,
                "total_questions": 20,
                "unattempted": 5,
                "tests": [
                    {
                        "test_name": "NEET Mock Test 1",
                        "test_date": "2024-01-15T10:30:00Z",
                        "questions": [
                            {
                                "question_id": 101,
                                "question": "A particle moves...",
                                "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
                                "correct_answer": "B",
                                "selected_answer": "B",
                                "is_correct": true,
                                "time_taken": 35
                            }
                        ]
                    }
                ]
            }
        ]
    """
    try:
        # Get completed test sessions ordered by end_time
        sessions_query = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).select_related('platform_test').order_by('end_time')
        
        if max_tests:
            sessions_query = sessions_query[:max_tests]
        
        sessions = list(sessions_query)
        
        if not sessions:
            return []
        
        session_ids = [s.id for s in sessions]
        
        # Get all test answers for these sessions
        answers_query = TestAnswer.objects.filter(
            session_id__in=session_ids
        ).select_related('question__topic', 'session', 'session__platform_test')
        
        # Filter by correctness
        if include == 'correct':
            answers_query = answers_query.filter(is_correct=True)
        elif include == 'wrong':
            answers_query = answers_query.filter(is_correct=False)
        
        answers = list(answers_query)
        
        if not answers:
            return []
        
        # Group answers by topic and then by test
        topic_data = defaultdict(lambda: {
            'topic_name': '',
            'subject': '',
            'chapter': '',
            'total_attempted': 0,
            'total_correct': 0,
            'total_time': 0,
            'tests': defaultdict(list)  # test_id -> list of questions
        })
        
        # Build session metadata map
        session_map = {}
        for session in sessions:
            test_name = session.get_test_name() if hasattr(session, 'get_test_name') else (
                session.platform_test.test_name if session.platform_test else f"Test {session.id}"
            )
            session_map[session.id] = {
                'test_name': test_name,
                'test_date': session.end_time.isoformat() if session.end_time else session.start_time.isoformat()
            }
        
        # Process answers
        for answer in answers:
            topic = answer.question.topic
            topic_key = f"{topic.id}_{topic.name}"
            
            # Initialize topic metadata
            if not topic_data[topic_key]['topic_name']:
                topic_data[topic_key]['topic_name'] = topic.name
                topic_data[topic_key]['subject'] = topic.subject
                topic_data[topic_key]['chapter'] = topic.chapter or ''
            
            # Track stats for accuracy calculation
            topic_data[topic_key]['total_attempted'] += 1
            if answer.is_correct:
                topic_data[topic_key]['total_correct'] += 1
            
            time_taken = answer.time_taken or 0
            topic_data[topic_key]['total_time'] += time_taken
            
            # Build question data
            q = answer.question
            options = {
                'A': q.option_a,
                'B': q.option_b,
                'C': q.option_c,
                'D': q.option_d,
            }
            
            question_entry = {
                'question_id': q.id,
                'question': q.question,
                'options': options,
                'correct_answer': q.correct_answer if q.correct_answer else None,
                'selected_answer': answer.selected_answer if answer.selected_answer else None,
                'is_correct': answer.is_correct if answer.is_correct is not None else None,
                'time_taken': time_taken
            }
            
            # Group by test
            topic_data[topic_key]['tests'][answer.session_id].append(question_entry)
        
        # Get total questions per topic from database
        topic_totals = {}
        topic_ids = [int(k.split('_')[0]) for k in topic_data.keys()]
        topic_counts = Question.objects.filter(topic_id__in=topic_ids).values('topic_id').annotate(
            total=Count('id')
        )
        for item in topic_counts:
            topic_totals[item['topic_id']] = item['total']
        
        # Build final result
        result = []
        for topic_key, data in topic_data.items():
            topic_id = int(topic_key.split('_')[0])
            
            # Calculate metrics
            accuracy = (data['total_correct'] / data['total_attempted'] * 100) if data['total_attempted'] > 0 else 0
            avg_time = (data['total_time'] / data['total_attempted']) if data['total_attempted'] > 0 else 0
            total_questions = topic_totals.get(topic_id, data['total_attempted'])
            unattempted = max(0, total_questions - data['total_attempted'])
            
            # Format tests
            tests_list = []
            for session_id, questions in data['tests'].items():
                if session_id in session_map:
                    tests_list.append({
                        'test_name': session_map[session_id]['test_name'],
                        'test_date': session_map[session_id]['test_date'],
                        'questions': questions
                    })
            
            # Sort tests by date (chronological order)
            tests_list.sort(key=lambda x: x['test_date'])
            
            result.append({
                'topic': data['topic_name'],
                'subject': data['subject'],
                'chapter': data['chapter'],
                'accuracy': round(accuracy, 2),
                'avg_time_sec': round(avg_time, 2),
                'total_questions': total_questions,
                'unattempted': unattempted,
                'tests': tests_list
            })
        
        # Sort by accuracy (descending for strengths, ascending for weaknesses)
        if include == 'correct':
            result.sort(key=lambda x: x['accuracy'], reverse=True)
        else:
            result.sort(key=lambda x: x['accuracy'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_topic_history_by_test for student {student_id}: {str(e)}")
        return []


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_strengths_history(request):
    """
    Get strengths history showing correctly answered questions grouped by topic and test.
    
    GET /api/insights/strengths-history/?max_tests=10
    
    Returns:
    {
        "status": "success",
        "data": [
            {
                "topic": "...",
                "subject": "...",
                "chapter": "...",
                "accuracy": 85.5,
                "avg_time_sec": 42.3,
                "total_questions": 20,
                "unattempted": 5,
                "tests": [
                    {
                        "test_name": "...",
                        "test_date": "...",
                        "questions": [...]
                    }
                ]
            }
        ]
    }
    """
    try:
        # Get authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        # Get max_tests parameter
        max_tests = request.GET.get('max_tests', None)
        if max_tests:
            try:
                max_tests = int(max_tests)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'max_tests must be an integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get topic history
        topics = get_topic_history_by_test(student_id, include='correct', max_tests=max_tests)
        
        return Response({
            'status': 'success',
            'data': topics,
            'count': len(topics)
        })
        
    except Exception as e:
        logger.error(f"Error in get_strengths_history: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weaknesses_history(request):
    """
    Get weaknesses history showing incorrectly answered questions grouped by topic and test.
    
    GET /api/insights/weaknesses-history/?max_tests=10
    
    Returns:
    {
        "status": "success",
        "data": [
            {
                "topic": "...",
                "subject": "...",
                "chapter": "...",
                "accuracy": 45.2,
                "avg_time_sec": 38.7,
                "total_questions": 20,
                "unattempted": 8,
                "tests": [
                    {
                        "test_name": "...",
                        "test_date": "...",
                        "questions": [...]
                    }
                ]
            }
        ]
    }
    """
    try:
        # Get authenticated student
        if not hasattr(request.user, 'student_id'):
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        student_id = request.user.student_id
        
        # Get max_tests parameter
        max_tests = request.GET.get('max_tests', None)
        if max_tests:
            try:
                max_tests = int(max_tests)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'max_tests must be an integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get topic history
        topics = get_topic_history_by_test(student_id, include='wrong', max_tests=max_tests)
        
        return Response({
            'status': 'success',
            'data': topics,
            'count': len(topics)
        })
        
    except Exception as e:
        logger.error(f"Error in get_weaknesses_history: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_insights_config(request):
    """
    Get the current default configuration for insights analysis.
    Useful for frontend to know current thresholds.
    
    Note: Threshold-based classification has been replaced with dynamic classification.
    This endpoint is maintained for backward compatibility.
    
    Returns:
    {
        "status": "success",
        "config": {
            "note": "Dynamic classification is now used instead of fixed thresholds"
        }
    }
    """
    return Response({
        'status': 'success',
        'config': {
            'note': 'Dynamic classification is now used instead of fixed thresholds',
            'features': {
                'study_plan': 'misconception-based',
                'strengths_weaknesses': 'dynamic-classification'
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_study_plan(request):
    """
    Generate a personalized study plan based on the student's misconceptions from recent tests.
    
    Analyzes wrong answers from the last N tests (default 5), groups them by topic and test,
    and uses LLM to identify repeated mistakes and generate top-5 actionable study recommendations.
    
    Query Parameters:
        max_tests (int, optional): Number of recent tests to analyze (default: 5)
    
    Returns:
    {
        "status": "success" | "insufficient_data" | "error",
        "analysis_summary": "Brief overview of mistake patterns",
        "recommendations": [
            {
                "rank": 1,
                "title": "Recommendation title",
                "reasoning": "Why this is important",
                "concept_gaps": ["Concept 1", "Concept 2"],
                "action_steps": ["Step 1", "Step 2", ...],
                "topics_to_review": ["Topic 1", "Topic 2"],
                "estimated_time": "2-3 hours",
                "priority": "high|medium",
                "affected_questions_count": 5
            }
        ],
        "supporting_data": {
            "topics": [...],  // Grouped wrong answers by topic and test
            "total_wrong_questions": int,
            "tests_analyzed": int
        }
    }
    """
    from neet_app.services.study_plan_service import generate_study_plan_from_misconceptions
    
    try:
        # Get student ID from authenticated user
        student = request.user.studentprofile
        student_id = student.id
        
        # Get max_tests parameter from query string (default 5)
        try:
            max_tests = int(request.query_params.get('max_tests', 5))
            if max_tests < 1:
                max_tests = 5
            if max_tests > 10:
                max_tests = 10  # Cap at 10 tests
        except (ValueError, TypeError):
            max_tests = 5
        
        # Generate study plan
        result = generate_study_plan_from_misconceptions(student_id, max_tests)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating study plan: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Failed to generate study plan: {str(e)}',
            'recommendations': [],
            'supporting_data': {}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
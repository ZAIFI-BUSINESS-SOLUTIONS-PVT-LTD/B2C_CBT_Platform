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

from ..models import StudentProfile, TestSession, TestAnswer, Question, Topic

logger = logging.getLogger(__name__)

# File-based insights cache directory
INSIGHTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'insights_cache')

# Log the cache directory setup
print(f"🗂️ INSIGHTS_CACHE_SETUP: Cache directory configured as: {INSIGHTS_CACHE_DIR}")
print(f"🗂️ INSIGHTS_CACHE_SETUP: Absolute cache directory: {os.path.abspath(INSIGHTS_CACHE_DIR)}")
print(f"🗂️ INSIGHTS_CACHE_SETUP: Current __file__: {__file__}")
print(f"🗂️ INSIGHTS_CACHE_SETUP: Directory of __file__: {os.path.dirname(__file__)}")
print(f"🗂️ INSIGHTS_CACHE_SETUP: Cache dir exists at startup: {os.path.exists(INSIGHTS_CACHE_DIR)}")

def get_insights_file_path(student_id):
    """Get the file path for storing student insights JSON."""
    file_path = os.path.join(INSIGHTS_CACHE_DIR, f'insights_{student_id}.json')
    print(f"📁 PATH_LOG: Cache directory: {INSIGHTS_CACHE_DIR}")
    print(f"📁 PATH_LOG: Generated file path: {file_path}")
    print(f"📁 PATH_LOG: Absolute path: {os.path.abspath(file_path)}")
    return file_path

def save_insights_to_file(student_id, insights_data):
    """Save insights data to a JSON file."""
    try:
        # Ensure the cache directory exists
        os.makedirs(INSIGHTS_CACHE_DIR, exist_ok=True)
        
        file_path = get_insights_file_path(student_id)
        
        # Log detailed information about the save operation
        print(f"💾 SAVE_INSIGHTS_LOG: Starting save operation for student {student_id}")
        print(f"💾 SAVE_INSIGHTS_LOG: Cache directory: {INSIGHTS_CACHE_DIR}")
        print(f"💾 SAVE_INSIGHTS_LOG: File path: {file_path}")
        print(f"💾 SAVE_INSIGHTS_LOG: Directory exists: {os.path.exists(INSIGHTS_CACHE_DIR)}")
        print(f"💾 SAVE_INSIGHTS_LOG: File exists before save: {os.path.exists(file_path)}")
        
        # Check if file exists and get its modification time
        if os.path.exists(file_path):
            mod_time_before = os.path.getmtime(file_path)
            print(f"💾 SAVE_INSIGHTS_LOG: File mod time before save: {mod_time_before}")
        else:
            print(f"💾 SAVE_INSIGHTS_LOG: File does not exist, will create new")
        
        # Save the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(insights_data, f, indent=2, ensure_ascii=False)
        
        # Verify the save was successful
        if os.path.exists(file_path):
            mod_time_after = os.path.getmtime(file_path)
            file_size = os.path.getsize(file_path)
            print(f"💾 SAVE_INSIGHTS_LOG: File successfully saved!")
            print(f"💾 SAVE_INSIGHTS_LOG: File mod time after save: {mod_time_after}")
            print(f"💾 SAVE_INSIGHTS_LOG: File size: {file_size} bytes")
            print(f"💾 SAVE_INSIGHTS_LOG: Data keys saved: {list(insights_data.keys()) if isinstance(insights_data, dict) else 'Not a dict'}")
        else:
            print(f"❌ SAVE_INSIGHTS_LOG: File does not exist after save operation!")
        
        print(f"💾 Insights saved to file for student {student_id}")
        return True
    except Exception as e:
        print(f"❌ SAVE_INSIGHTS_LOG: Exception during save: {type(e).__name__}: {e}")
        print(f"❌ Failed to save insights to file for student {student_id}: {e}")
        logger.error(f"Failed to save insights to file for student {student_id}: {e}")
        return False

def load_insights_from_file(student_id):
    """Load insights data from a JSON file."""
    try:
        file_path = get_insights_file_path(student_id)
        
        # Log detailed information about the load operation
        print(f"📂 LOAD_INSIGHTS_LOG: Starting load operation for student {student_id}")
        print(f"📂 LOAD_INSIGHTS_LOG: Cache directory: {INSIGHTS_CACHE_DIR}")
        print(f"📂 LOAD_INSIGHTS_LOG: File path: {file_path}")
        print(f"📂 LOAD_INSIGHTS_LOG: Directory exists: {os.path.exists(INSIGHTS_CACHE_DIR)}")
        print(f"📂 LOAD_INSIGHTS_LOG: File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            mod_time = os.path.getmtime(file_path)
            print(f"📂 LOAD_INSIGHTS_LOG: File size: {file_size} bytes")
            print(f"📂 LOAD_INSIGHTS_LOG: File mod time: {mod_time}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                insights_data = json.load(f)
            
            print(f"📂 LOAD_INSIGHTS_LOG: Data loaded successfully!")
            print(f"📂 LOAD_INSIGHTS_LOG: Data keys: {list(insights_data.keys()) if isinstance(insights_data, dict) else 'Not a dict'}")
            print(f"📂 Insights loaded from file for student {student_id}")
            return insights_data
        else:
            print(f"📂 LOAD_INSIGHTS_LOG: File not found, returning None")
            print(f"📂 No cached insights file found for student {student_id}")
            return None
    except Exception as e:
        print(f"❌ LOAD_INSIGHTS_LOG: Exception during load: {type(e).__name__}: {e}")
        print(f"❌ Failed to load insights from file for student {student_id}: {e}")
        logger.error(f"Failed to load insights from file for student {student_id}: {e}")
        return None

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
Act as a highly personalized NEET exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are an encouraging NEET exam tutor. A student has shown excellent performance in the following topics. 
Provide exactly 2 encouraging points in a supportive teacher tone that:
1. Praise their mastery and quick thinking
2. Motivate them to maintain this excellence
Keep each point to 1-2 sentences. Be specific about their achievements.

Topics data: {data}
""",
    
    'weaknesses': """
Act as a highly personalized NEET exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are a supportive NEET exam tutor. A student needs improvement in the following topics.
Provide exactly 2 constructive points in a positive, encouraging teacher tone that:
1. Identify areas needing focused revision without discouraging
2. Give a motivational push with specific improvement suggestions
Keep each point to 1-2 sentences. Focus on growth, not shortcomings.

Topics data: {data}
""",
    
    'study_plan': """
Act as a highly personalized NEET exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are a strategic NEET exam tutor creating a personalized study plan. Based on the student's performance across topics, provide exactly 2 actionable study suggestions that:
1. Mix targeted revision for weak topics with speed improvement strategies
2. Include balanced revision to keep strong topics sharp
Be specific and practical. Keep each suggestion to 1-2 sentences.

Performance data: {data}
""",
    
    'last_test_feedback': """
Act as a highly personalized NEET exam tutor. Carefully analyze the provided student data and deliver feedback with a warm, supportive, and individualized touch. For each metric or insight:
- Avoid using raw formatting like asterisks (**).
- Each point must be concise, specific, and limited to 18–20 words.
- Ensure every suggestion or observation is actionable, encouraging, and tailored to the student’s unique strengths and areas for improvement.

You are a friendly NEET exam tutor giving feedback on the student's most recent test performance.
Provide exactly 2 points in a warm, encouraging teacher tone that:
1. Notice improvements or strong performances from this latest session
2. Gently highlight areas that need attention from this test only
Keep each point to 1-2 sentences. Focus on recent progress and specific next steps.

Latest test data: {data}
"""
}
# Dynamic configuration for thresholds
DEFAULT_THRESHOLDS = {
    'strength_accuracy': 80.0,      # Minimum accuracy for strength (%)
    'weakness_accuracy': 60.0,      # Maximum accuracy for weakness (%)
    'time_multiplier': 1.2,         # Multiplier for average time threshold
    'min_attempts': 3,              # Minimum attempts needed for reliable metrics
}

def get_thresholds(request_data=None):
    """
    Get dynamic thresholds from request or use defaults.
    Allows frontend to customize classification criteria.
    """
    thresholds = DEFAULT_THRESHOLDS.copy()
    
    if request_data:
        # Update thresholds from request if provided
        if 'strength_accuracy' in request_data:
            thresholds['strength_accuracy'] = float(request_data['strength_accuracy'])
        if 'weakness_accuracy' in request_data:
            thresholds['weakness_accuracy'] = float(request_data['weakness_accuracy'])
        if 'time_multiplier' in request_data:
            thresholds['time_multiplier'] = float(request_data['time_multiplier'])
        if 'min_attempts' in request_data:
            thresholds['min_attempts'] = int(request_data['min_attempts'])
    
    return thresholds

def generate_llm_insights(insight_type, data):
    """
    Generate LLM-powered insights using Gemini API.
    
    Args:
        insight_type: Type of insight ('strengths', 'weaknesses', 'study_plan', 'last_test_feedback')
        data: Topic data to analyze
        
    Returns:
        dict: LLM-generated insights or fallback message
    """
    try:
        if not AVAILABLE_API_KEYS:
            print(f"❌ No Gemini API keys configured for {insight_type}")
            return {
                'status': 'warning',
                'message': 'Gemini API keys not configured',
                'insights': ['API configuration needed for AI insights', 'Using basic analysis for now']
            }
        
        if not data:
            print(f"⚠️ No data available for {insight_type} analysis")
            return {
                'status': 'info',
                'message': 'No data available for analysis',
                'insights': ['No test data available yet', 'Take some tests to get personalized insights']
            }
        
        print(f"🚀 Generating LLM insights for {insight_type} with data: {type(data)} items")
        
        # Get the appropriate prompt
        prompt_template = INSIGHT_PROMPTS.get(insight_type, INSIGHT_PROMPTS['strengths'])
        prompt = prompt_template.format(data=json.dumps(data, indent=2))
        
        print(f"📝 Using prompt template for {insight_type}")
        
        # Try each API key until one works (simple rotation)
        last_error = None
        for i, api_key in enumerate(AVAILABLE_API_KEYS):
            try:
                print(f"🤖 Trying Gemini API with key ending in ...{api_key[-6:]} (attempt {i+1}/{len(AVAILABLE_API_KEYS)})")
                
                # Configure with current API key
                genai.configure(api_key=api_key)
                
                # Configure Gemini model
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
                print(f"🤖 Calling Gemini API...")
                
                # Generate response with simpler configuration and safety settings
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=200,  # Reduced to prevent recursion
                        top_p=0.8,
                    ),
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                )
                
                print(f"✅ Gemini API responded successfully")
                
                # Parse response into individual points
                insights_text = response.text.strip()
                print(f"📖 Raw response: {insights_text[:100]}...")
                
                # Split into points (assuming numbered points or bullet points)
                insights = []
                lines = insights_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-') or line.startswith('*')):
                        # Remove numbering/bullets and clean up
                        clean_line = line.lstrip('0123456789.• -*').strip()
                        if clean_line:
                            insights.append(clean_line)
                
                # Fallback if parsing failed - just take first 2 sentences
                if len(insights) < 2:
                    sentences = insights_text.replace('\n', ' ').split('.')
                    insights = [s.strip() + '.' for s in sentences[:2] if s.strip()]
                
                print(f"📋 Parsed {len(insights)} insights for {insight_type}")
                
                return {
                    'status': 'success',
                    'message': 'AI insights generated successfully',
                    'insights': insights[:2]  # Ensure exactly 2 points
                }
                
            except RecursionError as e:
                print(f"❌ Recursion error with API key {i+1}, stopping attempts: {str(e)}")
                last_error = e
                break  # Stop trying other keys on recursion error
            except Exception as e:
                last_error = e
                error_msg = str(e)
                print(f"⚠️ API key {i+1} failed: {error_msg}")
                
                # Stop on certain critical errors
                if "recursion" in error_msg.lower() or "depth" in error_msg.lower():
                    print(f"❌ Recursion-related error detected, stopping retries")
                    break
                
                # Continue to next key for other errors
                if i >= len(AVAILABLE_API_KEYS) - 1:
                    break
                continue
        
        # If all API keys failed
        raise last_error if last_error else Exception("No API keys available")
        
    except Exception as e:
        print(f"❌ Error generating LLM insights for {insight_type}: {str(e)}")
        logger.error(f"Error generating LLM insights for {insight_type}: {str(e)}")
        
        # Provide fallback insights based on type
        fallback_insights = {
            'strengths': [
                'You are performing well in these topics - keep up the good work!',
                'Your accuracy and speed in these areas show strong understanding.'
            ],
            'weaknesses': [
                'These topics need more focused practice and revision.',
                'Consider reviewing fundamental concepts and practicing more questions.'
            ],
            'study_plan': [
                'Focus on weak topics while maintaining practice in strong areas.',
                'Balance conceptual understanding with speed improvement exercises.'
            ],
            'last_test_feedback': [
                'Your recent test shows areas for improvement.',
                'Keep practicing and reviewing to build consistency.'
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
        topic_data = defaultdict(lambda: {
            'attempted': 0,
            'correct': 0,
            'total_time': 0,
            'topic_name': '',
            'subject': '',
            'chapter': ''
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
        
        # Calculate metrics for each topic
        topic_metrics = {}
        overall_avg_time = total_time / total_attempted if total_attempted > 0 else 0
        
        for topic_key, data in topic_data.items():
            if data['attempted'] > 0:
                accuracy = (data['correct'] / data['attempted']) * 100
                avg_time = data['total_time'] / data['attempted']
                
                topic_metrics[topic_key] = {
                    'topic': data['topic_name'],
                    'subject': data['subject'],
                    'chapter': data['chapter'],
                    'accuracy': round(accuracy, 2),
                    'avg_time_sec': round(avg_time, 2),
                    'attempted': data['attempted'],
                    'correct': data['correct'],
                    'total_time': data['total_time']
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
    strengths = []
    weaknesses = []
    improvements = []
    
    time_threshold = overall_avg_time * thresholds['time_multiplier']
    strength_accuracy = thresholds['strength_accuracy']
    weakness_accuracy = thresholds['weakness_accuracy']
    min_attempts = thresholds['min_attempts']
    
    for topic_key, metrics in topic_metrics.items():
        # Skip topics with insufficient attempts for reliable analysis
        if metrics['attempted'] < min_attempts:
            continue
            
        accuracy = metrics['accuracy']
        avg_time = metrics['avg_time_sec']
        
        # Classification logic
        if accuracy >= strength_accuracy and avg_time <= time_threshold:
            # Strength: High accuracy AND reasonable time
            strengths.append({
                'topic': metrics['topic'],
                'accuracy': metrics['accuracy'],
                'avg_time_sec': metrics['avg_time_sec'],
                'subject': metrics['subject'],
                'chapter': metrics['chapter']
            })
        elif accuracy < weakness_accuracy or (accuracy < weakness_accuracy and avg_time > time_threshold):
            # Weakness: Low accuracy OR low accuracy with high time
            weaknesses.append({
                'topic': metrics['topic'],
                'accuracy': metrics['accuracy'],
                'avg_time_sec': metrics['avg_time_sec'],
                'subject': metrics['subject'],
                'chapter': metrics['chapter']
            })
        else:
            # Area for improvement: Moderate accuracy OR high accuracy but slow
            improvements.append({
                'topic': metrics['topic'],
                'accuracy': metrics['accuracy'],
                'avg_time_sec': metrics['avg_time_sec'],
                'subject': metrics['subject'],
                'chapter': metrics['chapter']
            })
    
    return {
        'strength_topics': strengths,
        'weak_topics': weaknesses,
        'improvement_topics': improvements
    }

def get_last_test_metrics(student_id, thresholds):
    """
    Get metrics for the student's most recent test session.
    
    Args:
        student_id: Student ID to analyze
        thresholds: Dict of classification thresholds
        
    Returns:
        dict: Last test topic metrics
    """
    try:
        # Get the most recent completed test session
        last_session = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).order_by('-end_time').first()
        
        if not last_session:
            return {'last_test_topics': []}
        
        # Calculate metrics for just this session
        session_metrics = calculate_topic_metrics(student_id, [last_session.id])
        
        if not session_metrics or 'topics' not in session_metrics:
            return {'last_test_topics': []}
        
        # Format for last test feedback (no classification, just metrics)
        last_test_topics = []
        min_attempts = thresholds['min_attempts']
        
        for topic_key, metrics in session_metrics['topics'].items():
            # Include topics even with fewer attempts for last test feedback
            if metrics['attempted'] >= 1:  # At least 1 attempt
                last_test_topics.append({
                    'topic': metrics['topic'],
                    'accuracy': metrics['accuracy'],
                    'avg_time_sec': metrics['avg_time_sec'],
                    'subject': metrics['subject'],
                    'chapter': metrics['chapter'],
                    'attempted': metrics['attempted']
                })
        
        return {'last_test_topics': last_test_topics}
        
    except Exception as e:
        logger.error(f"Error getting last test metrics for student {student_id}: {str(e)}")
        return {'last_test_topics': []}

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
        
        # Try to load from cache first (unless force_regenerate is True)
        if not force_regenerate:
            cached_insights = load_insights_from_file(student_id)
            if cached_insights:
                # Add cached flag to the response
                cached_insights['cached'] = True
                return Response(cached_insights)
        
        # Generate new insights if cache not found or force_regenerate is True
        print(f"🔄 Generating new insights for student {student_id}")
        
        # Get dynamic thresholds
        thresholds = get_thresholds(data)
        
        # Calculate overall metrics (all tests)
        all_metrics = calculate_topic_metrics(student_id)
        
        if not all_metrics or 'topics' not in all_metrics:
            empty_response = {
                'status': 'success',
                'data': {
                    'strength_topics': [],
                    'weak_topics': [],
                    'improvement_topics': [],
                    'last_test_topics': [],
                    'thresholds_used': thresholds,
                    'summary': {
                        'total_topics_analyzed': 0,
                        'total_tests_taken': 0,
                        'message': 'No test data available for analysis'
                    },
                    'cached': False
                }
            }
            # Save empty response to cache
            save_insights_to_file(student_id, empty_response)
            return Response(empty_response)
        
        # Classify topics based on all test data
        classification = classify_topics(
            all_metrics['topics'], 
            all_metrics['overall_avg_time'], 
            thresholds
        )
        
        # Get last test feedback
        last_test_data = get_last_test_metrics(student_id, thresholds)
        
        # Generate LLM insights for each category
        llm_insights = {}
        
        # Generate insights for strengths
        if classification['strength_topics']:
            llm_insights['strengths'] = generate_llm_insights('strengths', classification['strength_topics'])
        
        # Generate insights for weaknesses  
        if classification['weak_topics']:
            llm_insights['weaknesses'] = generate_llm_insights('weaknesses', classification['weak_topics'])
        
        # Generate study plan insights
        study_plan_data = {
            'weak_topics': classification['weak_topics'],
            'improvement_topics': classification['improvement_topics'],
            'strength_topics': classification['strength_topics']
        }
        llm_insights['study_plan'] = generate_llm_insights('study_plan', study_plan_data)
        
        # Generate last test feedback
        if last_test_data['last_test_topics']:
            llm_insights['last_test_feedback'] = generate_llm_insights('last_test_feedback', last_test_data['last_test_topics'])
        
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
        
        summary = {
            'total_topics_analyzed': total_topics,
            'total_tests_taken': total_tests,
            'strengths_count': len(classification['strength_topics']),
            'weaknesses_count': len(classification['weak_topics']),
            'improvements_count': len(classification['improvement_topics']),
            'overall_avg_time': round(all_metrics['overall_avg_time'], 2),
            'last_session_id': latest_session_id  # Add this for tracking
        }
        
        response_data = {
            'status': 'success',
            'data': {
                **classification,
                **last_test_data,
                'llm_insights': llm_insights,
                'thresholds_used': thresholds,
                'summary': summary,
                'cached': False
            }
        }
        
        # Save the generated insights to cache
        save_insights_to_file(student_id, response_data)
        
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
    Get cached insights data directly from the JSON file for the authenticated student.
    This endpoint reads the cached insights file and returns the data without regeneration.
    
    Returns:
    {
        "status": "success",
        "data": {...},           // Cached insights data
        "cached": true,
        "cache_info": {
            "file_exists": true,
            "file_size": 1234,
            "last_modified": "2025-08-13T12:40:00Z"
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
        
        # Try to load from cache file
        cached_insights = load_insights_from_file(student_id)
        
        if cached_insights:
            # Get file info for debugging
            file_path = get_insights_file_path(student_id)
            file_info = {
                'file_exists': os.path.exists(file_path),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'last_modified': None
            }
            
            if os.path.exists(file_path):
                import datetime
                mod_time = os.path.getmtime(file_path)
                file_info['last_modified'] = datetime.datetime.fromtimestamp(mod_time).isoformat()
            
            # Add cache info to response
            response_data = {
                'status': 'success',
                'data': cached_insights.get('data', cached_insights),  # Handle nested data structure
                'cached': True,
                'cache_info': file_info
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
                        'last_test_feedback': {
                            'status': 'info',
                            'message': 'No cached insights available',
                            'insights': ['Complete a test to get AI feedback on your performance!']
                        }
                    },
                    'summary': {
                        'total_topics_analyzed': 0,
                        'total_tests_taken': 0,
                        'strengths_count': 0,
                        'weaknesses_count': 0,
                        'improvements_count': 0
                    }
                },
                'cached': False,
                'cache_info': {
                    'file_exists': False,
                    'file_size': 0,
                    'last_modified': None
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
def get_insights_config(request):
    """
    Get the current default configuration for insights analysis.
    Useful for frontend to know current thresholds.
    
    Returns:
    {
        "status": "success",
        "config": {
            "strength_accuracy": 80.0,
            "weakness_accuracy": 60.0,
            "time_multiplier": 1.2,
            "min_attempts": 3
        }
    }
    """
    return Response({
        'status': 'success',
        'config': DEFAULT_THRESHOLDS
    })

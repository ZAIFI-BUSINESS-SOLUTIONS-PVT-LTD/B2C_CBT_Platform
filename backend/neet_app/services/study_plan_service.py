"""
Study Plan Generation Service using Student Misconceptions.
Collects wrong answers from recent tests and generates personalized study recommendations.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.db.models import Q, Prefetch
from neet_app.models import (
    TestAnswer, TestSession, PlatformTest, Question, Topic
)
from neet_app.services.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


# Prompt template for study plan generation based on misconceptions
STUDY_PLAN_PROMPT = """You are an expert NEET exam tutor analyzing a student's mistakes from their recent tests. Your goal is to identify repeated misconceptions, fundamental concept gaps, and provide actionable study recommendations.

**TASK:**
Analyze the wrong answers grouped by topic and test. For each wrong answer, you have:
- The question text
- The option the student selected
- The misconception associated with that wrong selection
- The test name and date

**YOUR ANALYSIS SHOULD:**
1. Identify which misconceptions appear repeatedly across multiple tests
2. Detect fundamental concept gaps (mistakes that suggest weak foundation understanding)
3. Distinguish between careless mistakes vs. systematic misunderstandings
4. Consider the chronological pattern (are mistakes getting better or worse?)
5. Rank all possible study interventions by:
   - IMPACT: How much improvement this would create
   - ACTIONABILITY: How clear and concrete the action steps are

**OUTPUT FORMAT:**
Return ONLY a valid JSON object with this structure:
{
  "analysis_summary": "Brief 2-3 sentence overview of the student's mistake patterns",
  "recommendations": [
    {
      "rank": 1,
      "title": "Clear, specific recommendation title (max 60 chars)",
      "reasoning": "Why this is important based on the mistakes observed (2-3 sentences)",
      "concept_gaps": ["Concept 1", "Concept 2"],
      "action_steps": [
        "Specific action step 1",
        "Specific action step 2",
        "Specific action step 3"
      ],
      "topics_to_review": ["Topic name 1", "Topic name 2"],
      "estimated_time": "e.g., '2-3 hours' or '1 week daily practice'",
      "priority": "high|medium",
      "affected_questions_count": 5
    }
  ]
}

**IMPORTANT RULES:**
- Return EXACTLY 5 recommendations (no more, no less)
- Rank them from most impactful and actionable (rank 1) to least (rank 5)
- Each recommendation must have 3-5 specific action steps
- Action steps must be concrete and specific (e.g., "Solve 10 numerical problems on Newton's Laws" not "Practice physics")
- DO NOT include markdown code fences or any text outside the JSON object
- Focus on the MOST impactful patterns, not every single mistake

**STUDENT'S WRONG ANSWERS:**

{misconceptions_data}

Return ONLY the JSON object with your analysis and top 5 recommendations."""


def normalize_option_key(selected_option: str) -> str:
    """
    Normalize the selected option to a standard key format.
    
    Args:
        selected_option: The option as stored (e.g., 'A', 'a', 'option_a', '1')
        
    Returns:
        str: Normalized key (e.g., 'option_a')
    """
    if not selected_option:
        return None
    
    option = str(selected_option).strip().lower()
    
    # Map variants to standard format
    option_map = {
        'a': 'option_a', '1': 'option_a', 'option_a': 'option_a',
        'b': 'option_b', '2': 'option_b', 'option_b': 'option_b',
        'c': 'option_c', '3': 'option_c', 'option_c': 'option_c',
        'd': 'option_d', '4': 'option_d', 'option_d': 'option_d',
        'e': 'option_e', '5': 'option_e', 'option_e': 'option_e',
    }
    
    return option_map.get(option, f'option_{option}')


def collect_wrong_answers_by_topic_and_test(student_id: int, max_tests: int = 5) -> Dict[str, Any]:
    """
    Collect all wrong answers from the student's recent tests, grouped by topic then by test.
    
    Args:
        student_id: The student's ID
        max_tests: Maximum number of recent tests to analyze (default 5)
        
    Returns:
        dict: Nested structure with topics -> tests -> questions
        {
            'topics': [
                {
                    'topic_id': int,
                    'topic_name': str,
                    'subject': str,
                    'total_wrong': int,
                    'tests': [
                        {
                            'test_id': int,
                            'test_name': str,
                            'test_date': str,
                            'questions': [
                                {
                                    'question_id': int,
                                    'question_text': str,
                                    'selected_option': str,
                                    'selected_option_text': str,
                                    'misconception': str,
                                    'answered_at': str
                                }
                            ]
                        }
                    ]
                }
            ],
            'total_wrong_questions': int,
            'tests_analyzed': int
        }
    """
    try:
        # Get the student's last N completed test sessions
        recent_sessions = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).select_related(
            'platform_test'
        ).order_by('-end_time')[:max_tests]
        
        if not recent_sessions:
            return {
                'topics': [],
                'total_wrong_questions': 0,
                'tests_analyzed': 0
            }
        
        session_ids = [s.id for s in recent_sessions]
        
        # Get all wrong answers from these sessions with related data
        wrong_answers = TestAnswer.objects.filter(
            session_id__in=session_ids,
            is_correct=False
        ).select_related(
            'question',
            'question__topic',
            'session',
            'session__platform_test'
        ).order_by('session__end_time', 'question__topic_id')
        
        # Group by topic, then by test
        topics_dict = {}
        total_wrong = 0
        
        for answer in wrong_answers:
            question = answer.question
            topic = question.topic
            session = answer.session
            platform_test = session.platform_test
            
            if not topic or not platform_test:
                continue
            
            topic_id = topic.id
            
            # Initialize topic entry if not exists
            if topic_id not in topics_dict:
                topics_dict[topic_id] = {
                    'topic_id': topic_id,
                    'topic_name': topic.name,
                    'subject': topic.subject,
                    'total_wrong': 0,
                    'tests': {}
                }
            
            test_id = platform_test.id
            
            # Initialize test entry if not exists
            if test_id not in topics_dict[topic_id]['tests']:
                topics_dict[topic_id]['tests'][test_id] = {
                    'test_id': test_id,
                    'test_name': platform_test.name,
                    'test_date': session.end_time.isoformat() if session.end_time else None,
                    'questions': []
                }
            
            # Get misconception for the selected option
            selected_option = answer.selected_answer
            normalized_key = normalize_option_key(selected_option)
            
            misconception = "Misconception not available"
            selected_option_text = selected_option
            
            if question.misconceptions and normalized_key:
                misconception = question.misconceptions.get(normalized_key, "Misconception not available")
                
                # Get the full option text from question options
                if question.options:
                    try:
                        options_data = question.options if isinstance(question.options, dict) else json.loads(question.options)
                        selected_option_text = options_data.get(normalized_key, selected_option)
                    except (json.JSONDecodeError, AttributeError):
                        pass
            
            # Add question data
            question_data = {
                'question_id': question.id,
                'question_text': question.question_text or "Question text not available",
                'selected_option': selected_option,
                'selected_option_text': selected_option_text,
                'misconception': misconception,
                'answered_at': answer.created_at.isoformat() if hasattr(answer, 'created_at') and answer.created_at else None
            }
            
            topics_dict[topic_id]['tests'][test_id]['questions'].append(question_data)
            topics_dict[topic_id]['total_wrong'] += 1
            total_wrong += 1
        
        # Convert nested dicts to lists and sort
        topics_list = []
        for topic_data in topics_dict.values():
            # Convert tests dict to list and sort by date
            tests_list = sorted(
                topic_data['tests'].values(),
                key=lambda t: t['test_date'] or ''
            )
            topic_data['tests'] = tests_list
            topics_list.append(topic_data)
        
        # Sort topics by total wrong count (descending)
        topics_list.sort(key=lambda t: t['total_wrong'], reverse=True)
        
        return {
            'topics': topics_list,
            'total_wrong_questions': total_wrong,
            'tests_analyzed': len(recent_sessions)
        }
        
    except Exception as e:
        logger.error(f"Error collecting wrong answers for student {student_id}: {str(e)}")
        return {
            'topics': [],
            'total_wrong_questions': 0,
            'tests_analyzed': 0
        }


def generate_study_plan_from_misconceptions(student_id: int, max_tests: int = 5) -> Dict[str, Any]:
    """
    Generate a personalized study plan by analyzing the student's misconceptions from recent tests.
    
    Args:
        student_id: The student's ID
        max_tests: Number of recent tests to analyze (default 5)
        
    Returns:
        dict: Study plan with recommendations and supporting data
        {
            'status': 'success' | 'error' | 'insufficient_data',
            'analysis_summary': str,
            'recommendations': [...],
            'supporting_data': {
                'topics': [...],
                'total_wrong_questions': int,
                'tests_analyzed': int
            }
        }
    """
    try:
        # Collect wrong answers grouped by topic and test
        data = collect_wrong_answers_by_topic_and_test(student_id, max_tests)
        
        if data['total_wrong_questions'] == 0:
            return {
                'status': 'insufficient_data',
                'message': 'No wrong answers found in recent tests. Complete more tests to get personalized study recommendations.',
                'recommendations': [],
                'supporting_data': data
            }
        
        # Prepare payload for LLM
        payload = json.dumps(data['topics'], indent=2)
        prompt = STUDY_PLAN_PROMPT.format(misconceptions_data=payload)
        
        # Call Gemini LLM
        try:
            gemini_client = GeminiClient()
            response_text = gemini_client.generate_content(
                prompt=prompt,
                model_override="gemini-2.5-flash"
            )
            
            if not response_text:
                raise ValueError("Empty response from LLM")
            
            # Parse JSON response
            # Remove markdown code fences if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response.split('```')[1]
                if cleaned_response.startswith('json'):
                    cleaned_response = cleaned_response[4:]
                cleaned_response = cleaned_response.strip()
            
            result = json.loads(cleaned_response)
            
            return {
                'status': 'success',
                'analysis_summary': result.get('analysis_summary', ''),
                'recommendations': result.get('recommendations', []),
                'supporting_data': data
            }
            
        except Exception as llm_error:
            logger.error(f"LLM call failed for student {student_id}: {str(llm_error)}")
            return {
                'status': 'error',
                'message': f'Failed to generate study plan: {str(llm_error)}',
                'recommendations': [],
                'supporting_data': data
            }
        
    except Exception as e:
        logger.error(f"Error generating study plan for student {student_id}: {str(e)}")
        return {
            'status': 'error',
            'message': f'An error occurred: {str(e)}',
            'recommendations': [],
            'supporting_data': {}
        }

"""
Misconception generation service using Gemini AI.
Analyzes MCQ questions to identify common misconceptions for each wrong option.
"""

import logging
import json
import re
from typing import List, Dict, Any
from django.db import transaction
from neet_app.models import Question, PlatformTest
from neet_app.services.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Prompt template for Gemini to analyze misconceptions
MISCONCEPTION_PROMPT = """You are an expert educator analyzing multiple-choice questions to identify student misconceptions.

For each question provided, analyze what specific misconception or misunderstanding a student would have if they chose each WRONG option instead of the correct answer.

**IMPORTANT OUTPUT FORMAT:**
- Return ONLY a valid JSON array
- Each element must have: "question_id", "misconceptions" (object with option keys)
- For the CORRECT option, use empty string ""
- For WRONG options, provide a concise 1-2 sentence explanation of the specific misconception
- DO NOT include markdown code fences, explanatory text, or any content outside the JSON array

**Example Output Format:**
[
  {{
    "question_id": 123,
    "misconceptions": {{
      "option_a": "Student confuses velocity with acceleration",
      "option_b": "",
      "option_c": "Student ignores the direction component of the vector",
      "option_d": "Student applies formula incorrectly by using mass instead of force"
    }}
  }}
]

**Questions to Analyze:**

{questions_data}

Return ONLY the JSON array with misconceptions for all questions."""


def build_questions_payload(questions: List[Question]) -> str:
    """
    Build formatted question data string for LLM prompt.
    
    Args:
        questions: List of Question model instances
        
    Returns:
        Formatted string containing question data
    """
    payload_parts = []
    
    for q in questions:
        question_text = f"""
Question ID: {q.id}
Subject: {q.topic.subject}
Topic: {q.topic.name}
Question: {q.question}
Option A: {q.option_a}
Option B: {q.option_b}
Option C: {q.option_c}
Option D: {q.option_d}
Correct Answer: {q.correct_answer}
---"""
        payload_parts.append(question_text)
    
    return "\n".join(payload_parts)


def parse_llm_response(llm_response: str) -> List[Dict[str, Any]]:
    """
    Parse LLM response and extract JSON data.
    Handles markdown code fences and malformed JSON.
    
    Args:
        llm_response: Raw response from LLM
        
    Returns:
        List of dicts with question_id and misconceptions
    """
    if not llm_response or not llm_response.strip():
        logger.warning("Empty LLM response received")
        return []
    
    # Remove markdown code fences
    cleaned = llm_response.strip()
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    # Try to extract JSON array if embedded in text
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
        else:
            logger.warning(f"LLM returned non-list JSON: {type(parsed)}")
            return []
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON directly: {e}")
        
        # Try regex extraction as fallback
        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
        if match:
            try:
                array_text = match.group(0)
                parsed = json.loads(array_text)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                logger.error(f"Regex-extracted JSON still invalid")
        
        logger.error(f"Could not extract valid JSON from response: {cleaned[:500]}")
        return []


@transaction.atomic
def generate_misconceptions_for_test(test_id: int, batch_size: int = 20) -> Dict[str, Any]:
    """
    Generate misconceptions for all MCQ questions in a test.
    Questions are grouped by subject and processed in batches.
    
    Args:
        test_id: PlatformTest ID
        batch_size: Number of questions to process per LLM call
        
    Returns:
        Dict with statistics: {
            'success': bool,
            'total_questions': int,
            'processed': int,
            'failed': int,
            'subjects_processed': list
        }
    """
    try:
        # Get test
        test = PlatformTest.objects.get(id=test_id)
        
        logger.info(f"Starting misconception generation for test {test_id}: {test.test_name}")
        
        # Get all MCQ questions for this test (exclude NVT)
        questions = Question.objects.filter(
            institution=test.institution,
            institution_test_name=test.test_name,
            exam_type=test.exam_type
        ).exclude(
            question_type__iexact='NVT'
        ).select_related('topic')
        
        if not questions.exists():
            logger.info(f"No MCQ questions found for test {test_id}")
            return {
                'success': True,
                'total_questions': 0,
                'processed': 0,
                'failed': 0,
                'subjects_processed': []
            }
        
        # Group questions by subject
        questions_by_subject = {}
        for q in questions:
            subject = q.topic.subject
            if subject not in questions_by_subject:
                questions_by_subject[subject] = []
            questions_by_subject[subject].append(q)
        
        # Initialize Gemini client with specific model
        gemini_client = GeminiClient()
        if not gemini_client.is_available():
            logger.error("Gemini client not available for misconception generation")
            return {
                'success': False,
                'total_questions': questions.count(),
                'processed': 0,
                'failed': questions.count(),
                'error': 'Gemini client not available',
                'subjects_processed': []
            }
        
        # Override model to gemini-2.5-flash
        gemini_client.model_name = 'gemini-2.5-flash'
        
        total_processed = 0
        total_failed = 0
        subjects_processed = []
        
        # Process each subject — send one request per subject (no inner batching)
        for subject, subject_questions in questions_by_subject.items():
            logger.info(f"Processing {len(subject_questions)} questions for subject: {subject}")
            subjects_processed.append(subject)

            try:
                # Build payload for the entire subject
                questions_data = build_questions_payload(subject_questions)
                prompt = MISCONCEPTION_PROMPT.format(questions_data=questions_data)

                # Call LLM once per subject
                logger.info(f"Sending {len(subject_questions)} questions to Gemini for subject: {subject}")
                llm_response = gemini_client.generate_response(prompt)

                if not llm_response:
                    logger.error(f"Empty response from Gemini for subject {subject}")
                    total_failed += len(subject_questions)
                    continue

                # Parse response
                results = parse_llm_response(llm_response)

                if not results:
                    logger.error(f"Failed to parse LLM response for subject {subject}")
                    total_failed += len(subject_questions)
                    continue

                # Map results back to questions using question_id
                results_map = {r['question_id']: r['misconceptions'] for r in results if 'question_id' in r and 'misconceptions' in r}

                # Update questions for this subject
                for question in subject_questions:
                    if question.id in results_map:
                        question.misconceptions = results_map[question.id]
                        question.save(update_fields=['misconceptions'])
                        total_processed += 1
                        logger.debug(f"Updated misconceptions for question {question.id}")
                    else:
                        logger.warning(f"No misconceptions returned for question {question.id}")
                        total_failed += 1

            except Exception as e:
                logger.exception(f"Error processing subject {subject}: {e}")
                total_failed += len(subject_questions)
        
        return {
            'success': True,
            'total_questions': questions.count(),
            'processed': total_processed,
            'failed': total_failed,
            'subjects_processed': subjects_processed
        }
        
    except PlatformTest.DoesNotExist:
        logger.error(f"Test {test_id} not found")
        return {
            'success': False,
            'error': f'Test {test_id} not found',
            'total_questions': 0,
            'processed': 0,
            'failed': 0,
            'subjects_processed': []
        }
    except Exception as e:
        logger.exception(f"Unexpected error in generate_misconceptions_for_test: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_questions': 0,
            'processed': 0,
            'failed': 0,
            'subjects_processed': []
        }

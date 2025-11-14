"""
Zone Insights Service
Generates test-specific, subject-wise insights with Steady/Edge/Focus zones.
Each zone contains 2 actionable points for student improvement.
"""

import logging
import json
from typing import Dict, List, Optional
from django.db.models import Q

logger = logging.getLogger(__name__)

# LLM Prompt for zone-based insights
ZONE_INSIGHT_PROMPT = """
You are an expert NEET and JEE exam tutor analyzing a student's test performance for {subject}. 
Analyze the following questions and their answers to generate exactly 6 insights grouped into 3 zones: 
🟢 Steady Zone (2 points): Areas where the student is consistently performing well - high accuracy, good speed, solid conceptual understanding 
🟠 Edge Zone (2 points): Borderline concepts needing mild improvement - moderate accuracy, timing issues, or inconsistent performance 
🔴 Focus Zone (2 points): Critical weak areas requiring priority attention - low accuracy, conceptual gaps, or recurring mistakes 
RULES: 
- Each point must be 15-25 words maximum 
- Be specific and actionable 
- Avoid formatting markers like ** or asterisks 
- Analyze question-by-question patterns (correctness, speed, topic consistency) 
- Prioritize insights by impact and actionability 
- Focus on patterns across multiple questions, not individual questions 
- Be encouraging and constructive in tone 
- All insights must strictly reference academic concepts, test-taking strategy, or subject-specific topics. Avoid personal or emotional analysis.
Questions Data ({total_questions} 
questions analyzed): {questions_json} 
Return EXACTLY 6 insights in this JSON format: 
{{ 
"steady_zone": ["point 1", "point 2"], 
"edge_zone": ["point 1", "point 2"], 
"focus_zone": ["point 1", "point 2"]
}}
"""


def extract_subject_questions(test_session_id: int, subject: str) -> List[Dict]:
    """
    Extract questions for a specific subject from a test session.
    
    Args:
        test_session_id: ID of the test session
        subject: Subject name (Physics, Chemistry, Botany, Zoology, Math)
        
    Returns:
        List of question dictionaries with answer data
    """
    try:
        from ..models import TestSession, TestAnswer
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Get subject-specific topic IDs (including Math)
        subject_map = {
            'Physics': test_session.physics_topics,
            'Chemistry': test_session.chemistry_topics,
            'Botany': test_session.botany_topics,
            'Zoology': test_session.zoology_topics,
            'Math': test_session.math_topics
        }
        
        topic_ids = subject_map.get(subject, [])
        
        if not topic_ids:
            print(f"⚠️ No topics found for {subject} in test {test_session_id}")
            return []
        
        # Get answers for those topics
        answers = TestAnswer.objects.filter(
            session_id=test_session_id,
            question__topic_id__in=topic_ids
        ).select_related('question', 'question__topic').order_by('id')
        
    # Format questions for LLM (include all subject answers)
        questions_data = []
        for answer in answers:
            q = answer.question
            
            # Prepare options dict
            options = {
                'A': q.option_a,
                'B': q.option_b,
                'C': q.option_c,
                'D': q.option_d,
            }
            
            question_entry = {
                'question_id': q.id,
                        # Include full question text (do not truncate) so LLM sees complete context
                'question': q.question if q.question else '',
                'options': options,
                'correct_answer': q.correct_answer if q.correct_answer else None,
                'selected_answer': answer.selected_answer if answer.selected_answer else None,
                'is_correct': answer.is_correct,
                'time_taken': answer.time_taken or 0,
                # 'topic' intentionally omitted from LLM payload to avoid leaking explicit topic labels
            }
            
            questions_data.append(question_entry)
        
        total_questions = len(questions_data)
        # Enforce maximum of 45 questions to keep LLM prompt size bounded
        if total_questions > 45:
            logger.info(
                "Truncating %d questions to first 45 for subject %s in test %d",
                total_questions,
                subject,
                test_session_id
            )
            questions_data = questions_data[:45]

        print(f"📊 Extracted {len(questions_data)} questions for {subject} from test {test_session_id}")
        return questions_data
        
    except Exception as e:
        logger.error(f"Error extracting questions for {subject} in test {test_session_id}: {str(e)}")
        return []


def generate_zone_insights_for_subject(subject: str, questions: List[Dict]) -> Dict[str, List[str]]:
    """
    Generate zone insights for a subject using LLM.
    
    Args:
        subject: Subject name
        questions: List of question dictionaries
        
    Returns:
        Dict with steady_zone, edge_zone, focus_zone (each containing 2 points)
    """
    try:
        if not questions:
            print(f"⚠️ No questions provided for {subject}")
            return get_fallback_zones(subject, "No questions available")

        # Ensure we send at most 45 questions and truncate overly long question text
        def _truncate_questions_for_prompt(qs: List[Dict], max_questions: int = 45, max_text_len: int = 1000) -> List[Dict]:
            total = len(qs)
            if total > max_questions:
                logger.info(
                    "Truncating questions payload from %d to %d for subject %s",
                    total,
                    max_questions,
                    subject,
                )
                qs = qs[:max_questions]

            # Truncate long text fields to avoid extremely large prompts
            for q in qs:
                if 'question' in q and isinstance(q['question'], str) and len(q['question']) > max_text_len:
                    q['question'] = q['question'][:max_text_len] + '...'
                if 'options' in q and isinstance(q['options'], dict):
                    for k, v in list(q['options'].items()):
                        if isinstance(v, str) and len(v) > max_text_len:
                            q['options'][k] = v[:max_text_len] + '...'
            return qs

        questions = _truncate_questions_for_prompt(questions)
        
        # Import GeminiClient
        try:
            from ..services.ai.gemini_client import GeminiClient
        except ImportError:
            from neet_app.services.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        if not client.is_available():
            print(f"❌ Gemini client not available for {subject} zone insights")
            return get_fallback_zones(subject, "AI service unavailable")
        
        # Build prompt
        questions_json = json.dumps(questions, indent=2)
        prompt = ZONE_INSIGHT_PROMPT.format(
            subject=subject,
            total_questions=len(questions),
            questions_json=questions_json
        )
        
        logger.info(f"🚀 Generating zone insights for {subject} using {client.model_name}")
        
        # Call LLM (guard against lower-level errors from gRPC / client libraries)
        try:
            llm_response = client.generate_response(prompt)
        except BaseException as e:
            # Catch BaseException to handle fatal errors originating from gRPC C extensions
            logger.error(
                "LLM client raised a fatal error for subject %s: %s",
                subject,
                str(e)
            )
            return get_fallback_zones(subject, f"LLM call failed: {str(e)}")
        
        if not llm_response:
            print(f"❌ Empty response from LLM for {subject}")
            return get_fallback_zones(subject, "Empty LLM response")
        
        # Parse response
        zones = parse_llm_zone_response(llm_response, subject)
        
        print(f"✅ Zone insights generated for {subject}")
        return zones
        
    except Exception as e:
        logger.error(f"Error generating zone insights for {subject}: {str(e)}")
        return get_fallback_zones(subject, f"Error: {str(e)}")


def parse_llm_zone_response(llm_response: str, subject: str) -> Dict[str, List[str]]:
    """
    Parse LLM response to extract zone insights.
    
    Args:
        llm_response: Raw LLM response text
        subject: Subject name (for logging)
        
    Returns:
        Dict with steady_zone, edge_zone, focus_zone
    """
    try:
        # Try to parse as JSON first
        response_text = llm_response.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            # Remove first and last lines (``` markers)
            response_text = '\n'.join(lines[1:-1] if len(lines) > 2 else lines)
            response_text = response_text.strip()
        
        # Try direct JSON parse
        try:
            zones = json.loads(response_text)
            
            # Validate structure
            if all(key in zones for key in ['steady_zone', 'edge_zone', 'focus_zone']):
                # Ensure each zone has exactly 2 points
                for zone_key in ['steady_zone', 'edge_zone', 'focus_zone']:
                    if not isinstance(zones[zone_key], list):
                        zones[zone_key] = [str(zones[zone_key])]
                    
                    # Truncate to 2 points
                    zones[zone_key] = zones[zone_key][:2]
                    
                    # Pad with fallback if less than 2
                    while len(zones[zone_key]) < 2:
                        zones[zone_key].append(f"Additional analysis needed for {subject}")
                
                print(f"✅ Successfully parsed zone insights for {subject}")
                return zones
        except json.JSONDecodeError:
            pass
        
        # Fallback: Try to extract zones from text format
        zones = {
            'steady_zone': [],
            'edge_zone': [],
            'focus_zone': []
        }
        
        lines = response_text.split('\n')
        current_zone = None
        
        for line in lines:
            line = line.strip()
            
            # Detect zone headers
            if 'steady' in line.lower() or '🟢' in line:
                current_zone = 'steady_zone'
                continue
            elif 'edge' in line.lower() or '🟠' in line:
                current_zone = 'edge_zone'
                continue
            elif 'focus' in line.lower() or '🔴' in line:
                current_zone = 'focus_zone'
                continue
            
            # Extract points (bullets, numbers, or plain text)
            if current_zone and line:
                # Remove bullet points, numbers, etc.
                clean_line = line.lstrip('•-*0123456789.').strip()
                if clean_line and len(clean_line) > 10:  # Minimum meaningful length
                    zones[current_zone].append(clean_line)
        
        # Ensure exactly 2 points per zone
        for zone_key in ['steady_zone', 'edge_zone', 'focus_zone']:
            zones[zone_key] = zones[zone_key][:2]
            while len(zones[zone_key]) < 2:
                zones[zone_key].append(f"Continue practicing {subject} for better insights")
        
        if any(len(z) > 0 for z in zones.values()):
            print(f"✅ Parsed zone insights from text format for {subject}")
            return zones
        
        # If all parsing fails, return fallback
        print(f"⚠️ Could not parse LLM response for {subject}, using fallback")
        return get_fallback_zones(subject, "Parsing failed")
        
    except Exception as e:
        logger.error(f"Error parsing zone response for {subject}: {str(e)}")
        return get_fallback_zones(subject, f"Parse error: {str(e)}")


def get_fallback_zones(subject: str, reason: str) -> Dict[str, List[str]]:
    """
    Generate fallback zone insights when LLM is unavailable or fails.
    
    Args:
        subject: Subject name
        reason: Reason for fallback
        
    Returns:
        Dict with fallback zone insights
    """
    print(f"⚠️ Using fallback zones for {subject}: {reason}")
    
    return {
        'steady_zone': [
            f"Your {subject} performance is being analyzed for steady areas.",
            f"Complete more {subject} questions to identify consistent strengths."
        ],
        'edge_zone': [
            f"Some {subject} concepts need mild improvement in accuracy or speed.",
            f"Focus on time management and revisiting borderline {subject} topics."
        ],
        'focus_zone': [
            f"Certain {subject} areas need priority attention and deeper understanding.",
            f"Dedicate extra practice time to weak {subject} concepts identified."
        ]
    }


def generate_all_subject_zones(test_session_id: int) -> Dict[str, Dict[str, List[str]]]:
    """
    Generate zone insights for all subjects in a test session.
    This is the main orchestrator function - dynamically detects which subjects are in the test.
    
    Args:
        test_session_id: ID of the test session
        
    Returns:
        Dict mapping subject names to their zone insights
    """
    try:
        from ..models import TestSession, TestSubjectZoneInsight
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Dynamically determine which subjects are present in this test (including Math)
        subjects_to_process = []
        
        if test_session.physics_topics:
            subjects_to_process.append('Physics')
        if test_session.chemistry_topics:
            subjects_to_process.append('Chemistry')
        if test_session.botany_topics:
            subjects_to_process.append('Botany')
        if test_session.zoology_topics:
            subjects_to_process.append('Zoology')
        if test_session.math_topics:
            subjects_to_process.append('Math')
        
        if not subjects_to_process:
            print(f"⚠️ No subjects found in test {test_session_id}")
            return {}
        
        print(f"🎯 Generating zone insights for test {test_session_id}")
        print(f"📚 Subjects to process: {', '.join(subjects_to_process)}")
        
        results = {}
        
        for subject in subjects_to_process:
            try:
                # Extract questions for this subject
                questions = extract_subject_questions(test_session_id, subject)
                
                if not questions:
                    print(f"⚠️ No questions found for {subject}, skipping")
                    continue
                
                # Generate zone insights
                zones = generate_zone_insights_for_subject(subject, questions)
                
                # Save to database
                insight, created = TestSubjectZoneInsight.objects.update_or_create(
                    test_session_id=test_session_id,
                    subject=subject,
                    defaults={
                        'student_id': test_session.student_id,
                        'steady_zone': zones['steady_zone'],
                        'edge_zone': zones['edge_zone'],
                        'focus_zone': zones['focus_zone'],
                        'questions_analyzed': questions  # Store for debugging
                    }
                )
                
                action = "Created" if created else "Updated"
                print(f"💾 {action} zone insights for {subject} in test {test_session_id}")
                
                results[subject] = zones
                
            except Exception as e:
                logger.error(f"Error processing {subject} for test {test_session_id}: {str(e)}")
                print(f"❌ Failed to process {subject}: {str(e)}")
                continue
        
        print(f"✅ Zone insights generation complete for test {test_session_id}")
        print(f"📊 Processed {len(results)}/{len(subjects_to_process)} subjects successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in generate_all_subject_zones for test {test_session_id}: {str(e)}")
        print(f"❌ Failed to generate zone insights: {str(e)}")
        return {}

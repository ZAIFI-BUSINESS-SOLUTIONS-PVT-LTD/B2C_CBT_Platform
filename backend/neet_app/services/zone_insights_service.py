"""
Zone Insights Service - Checkpoint-based diagnostic system
Generates subject-wise checkpoints with problem identification and action plans.
"""

import logging
import json
from typing import Dict, List, Optional
from django.db.models import Q

logger = logging.getLogger(__name__)

# LLM Prompt for checkpoint generation (wrong/skipped questions)
CHECKPOINT_PROMPT = """**Task**: Generate a comprehensive diagnostic and action plan for a NEET student by identifying both problems AND solutions for their weak topics.
**Context**: You are an AI mentor helping students understand both:
1. **WHAT went wrong** (diagnostic checklist of problems)
2. **HOW to fix it** (actionable steps to improve)
For each checkpoint, you will provide BOTH the problem identification AND the corresponding action plan.
**Input Data Provided**:
- Multiple weak topics with performance metrics (accuracy)
- Wrong questions from each topic including:
  - Question text, options, selected answer, correct answer
  - Misconception   
**Your Task**:
1. Analyze ALL weak topics and wrong answers provided FOR THIS SUBJECT
2. Identify the most critical problems across topics IN THIS SUBJECT
3. For EACH problem, also determine the most impactful action to fix it
4. Generate a **specific subtopic name** that precisely describes the narrow area of difficulty within the topic
5. Rank checkpoints by:
   - **Severity/Impact**: How much this issue affects overall performance
   - **Actionability**: How clear and achievable the solution is
6. Select ONLY the **top 2 most critical problem-solution pairs** for THIS SUBJECT
**Checkpoint Requirements**:
- Each checklist item must be **10-15 words** maximum
- Each action plan item must be **10-15 words** maximum
- **Subtopic** must be a specific, narrow area within the topic.
- Checklist must identify WHAT went wrong (diagnostic, factual)
- Action plan must describe HOW to fix it (prescriptive, actionable)
- Use simple, easy-to-understand Indian-English
- Each item should be at the reading level of a 10-year-old Indian student. Use only very simple English words. Do NOT use difficult or formal words.
- Be specific and directly tied to their actual mistakes
- Reference the specific topic/subject in context
**Output Format (strict JSON)**:
[
  {{
    "topic": "Topic name",
    "subject": "Subject name",
    "subtopic": "Specific narrow area within topic",
    "accuracy": 0.45,
    "checklist": "Specific problem or mistake identified (10-15 words)",
    "action_plan": "Specific action to fix this problem (10-15 words)",
    "citation": [5, 12, 18]
  }},
  {{
    "topic": "Topic name",
    "subject": "Subject name",
    "subtopic": "Specific narrow area within topic",
    "accuracy": 0.32,
    "checklist": "Specific problem or mistake identified (10-15 words)",
    "action_plan": "Specific action to fix this problem (10-15 words)",
    "citation": [7, 22]
  }}
]
**Citation Requirements**:
- Each checkpoint MUST include a "citation" field listing the question numbers that support this insight
- Citation format: array of question numbers, e.g., [5, 12, 18]
- Include 2-5 question numbers per checkpoint as evidence
- Select questions that best demonstrate the specific problem identified in the checklist
- Questions in citation should be from the wrong_questions data provided for that topic
**Guidelines**:
- Return EXACTLY 2 checkpoint pairs for THIS SUBJECT (not more, not less)
- These 2 should be the highest-impact issues for THIS SUBJECT
- Each checklist-action pair must be logically connected (the action fixes the checklist problem)
- Checklist uses diagnostic language: "confused", "mistook", "missed", "incorrectly applied"
- Action plan uses prescriptive language: "practice", "review", "memorize", "understand"
- Both should directly reflect the student's actual wrong answers
- Keep tone supportive and constructive
- Both checkpoints can be from the same topic if they're high-impact
**Important**:
- Return ONLY the JSON array of exactly 2 items for THIS SUBJECT
- No explanations, no notes, no markdown code blocks
- Strictly follow the format above
- Ensure checklist and action_plan are paired and related for each item

Subject: {subject}
Topics Data:
{topics_json}
"""

# Fallback prompt for when student has no wrong/skipped questions (all correct)
CORRECT_UNDERSTANDING_PROMPT = """**Task**: Generate insights about a NEET student's correct understanding and areas for further focus based on their correct answers.
**Context**: This student answered all questions correctly for this subject. Identify what mental models they demonstrated and what they should focus on to maintain and expand this mastery.
**Input Data Provided**:
- Multiple topics with all correct answers
- Question text, options, selected answer, correct answer for each
**Your Task**:
1. Analyze correct answers to identify strong conceptual understanding
2. Determine which mental models or reasoning patterns led to success
3. Suggest specific areas within this subject for further deepening
4. Generate exactly 2 checkpoints focusing on strength reinforcement
**Checkpoint Requirements**:
- Each checklist item: describe WHAT the student understood correctly (10-15 words)
- Each action plan item: suggest HOW to build on this strength (10-15 words)
- Use simple, easy-to-understand Indian-English
- Be encouraging and specific
**Output Format (strict JSON)**:
[
  {{
    "topic": "Topic name",
    "subject": "Subject name",
    "subtopic": "Specific area of mastery",
    "accuracy": 1.0,
    "checklist": "What the student understood correctly (10-15 words)",
    "action_plan": "How to deepen or expand this understanding (10-15 words)",
    "citation": [1, 3, 7]
  }},
  {{
    "topic": "Topic name",
    "subject": "Subject name",
    "subtopic": "Specific area of mastery",
    "accuracy": 1.0,
    "checklist": "What the student understood correctly (10-15 words)",
    "action_plan": "How to deepen or expand this understanding (10-15 words)",
    "citation": [2, 5, 9]
  }}
]
**Important**:
- Return ONLY the JSON array of exactly 2 items for THIS SUBJECT
- No explanations, no notes, no markdown code blocks
- Strictly follow the format above

Subject: {subject}
Topics Data:
{topics_json}
"""


def extract_wrong_and_skipped_questions(test_session_id: int, subject: str) -> Dict:
    """
    Extract wrong and skipped questions for a subject, grouped by topic.
    
    Args:
        test_session_id: ID of the test session
        subject: Subject name (Physics, Chemistry, Botany, Zoology, Biology, Math)
        
    Returns:
        Dict with topic-grouped data including accuracy, question count, avg time, and questions array
    """
    try:
        from ..models import TestSession, TestAnswer, Topic
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Get subject-specific topic names
        subject_map = {
            'Physics': test_session.physics_topics,
            'Chemistry': test_session.chemistry_topics,
            'Botany': test_session.botany_topics,
            'Zoology': test_session.zoology_topics,
            'Biology': test_session.biology_topics,
            'Math': test_session.math_topics
        }
        
        topic_names = subject_map.get(subject, [])
        
        if not topic_names:
            print(f"⚠️ No topics found for {subject} in test {test_session_id}")
            return {}
        
        # Convert topic names to IDs
        topic_objects = Topic.objects.filter(name__in=topic_names)
        topic_ids = list(topic_objects.values_list('id', flat=True))
        
        if not topic_ids:
            print(f"⚠️ Could not find topic IDs for {subject} topics: {topic_names}")
            return {}
        
        # Get ALL answers for those topics
        all_answers = TestAnswer.objects.filter(
            session_id=test_session_id,
            question__topic_id__in=topic_ids
        ).select_related('question', 'question__topic').order_by('id')
        
        # Group by topic and separate wrong/skipped from all
        from collections import defaultdict
        topic_data = defaultdict(lambda: {
            'topic_name': '',
            'total_questions': 0,
            'correct_count': 0,
            'wrong_skipped_questions': [],
            'total_time': 0,
            'question_count': 0
        })
        
        for answer in all_answers:
            q = answer.question
            topic = q.topic
            topic_name = topic.name
            
            # Track overall metrics
            topic_data[topic_name]['topic_name'] = topic_name
            topic_data[topic_name]['total_questions'] += 1
            
            # Count correct answers for accuracy calculation
            if answer.is_correct:
                topic_data[topic_name]['correct_count'] += 1
                continue  # Skip correct answers for checkpoint generation
            
            # Extract misconception for wrong answer
            misconception_text = None
            if not answer.is_correct and answer.selected_answer:
                # Get misconception from Question.misconceptions JSON
                misconceptions = q.misconceptions or {}
                # misconceptions format: {"option_a": "text", "option_b": "text", ...}
                selected_option = answer.selected_answer.upper()
                misconception_text = misconceptions.get(f"option_{selected_option.lower()}", None)
            
            # Build question data for wrong/skipped questions
            question_entry = {
                'question_id': q.id,
                'question': q.question if q.question else '',
                'options': {
                    'A': q.option_a,
                    'B': q.option_b,
                    'C': q.option_c,
                    'D': q.option_d,
                },
                'correct_answer': q.correct_answer if q.correct_answer else None,
                'selected_answer': answer.selected_answer if answer.selected_answer else None,
                'is_correct': answer.is_correct,
                'time_taken': answer.time_taken or 0,
                'misconception': misconception_text
            }
            
            topic_data[topic_name]['wrong_skipped_questions'].append(question_entry)
            topic_data[topic_name]['total_time'] += (answer.time_taken or 0)
            topic_data[topic_name]['question_count'] += 1
        
        # Calculate accuracy and avg time for each topic
        result = []
        for topic_name, data in topic_data.items():
            if data['total_questions'] == 0:
                continue
                
            accuracy = data['correct_count'] / data['total_questions']
            avg_time = data['total_time'] / data['question_count'] if data['question_count'] > 0 else 0
            
            # Limit questions per topic to avoid huge payloads
            questions = data['wrong_skipped_questions'][:20]
            
            result.append({
                'topic': topic_name,
                'accuracy': round(accuracy, 2),
                'no_of_questions': data['total_questions'],
                'avg_time': round(avg_time, 1),
                'questions': questions
            })
        
        print(f"📊 Extracted {len(result)} topics with wrong/skipped questions for {subject}")
        return {'topics': result}
        
    except Exception as e:
        logger.error(f"Error extracting wrong/skipped questions for {subject} in test {test_session_id}: {str(e)}")
        return {}


def extract_correct_questions(test_session_id: int, subject: str) -> Dict:
    """
    Extract correct questions when no wrong/skipped questions exist.
    
    Args:
        test_session_id: ID of the test session
        subject: Subject name
        
    Returns:
        Dict with topic-grouped correct questions
    """
    try:
        from ..models import TestSession, TestAnswer, Topic
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Get subject-specific topic names
        subject_map = {
            'Physics': test_session.physics_topics,
            'Chemistry': test_session.chemistry_topics,
            'Botany': test_session.botany_topics,
            'Zoology': test_session.zoology_topics,
            'Biology': test_session.biology_topics,
            'Math': test_session.math_topics
        }
        
        topic_names = subject_map.get(subject, [])
        
        if not topic_names:
            return {}
        
        # Convert topic names to IDs
        topic_objects = Topic.objects.filter(name__in=topic_names)
        topic_ids = list(topic_objects.values_list('id', flat=True))
        
        if not topic_ids:
            print(f"⚠️ Could not find topic IDs for {subject} topics: {topic_names}")
            return {}
        
        # Get only correct answers
        correct_answers = TestAnswer.objects.filter(
            session_id=test_session_id,
            question__topic_id__in=topic_ids,
            is_correct=True
        ).select_related('question', 'question__topic').order_by('id')[:20]
        
        from collections import defaultdict
        topic_data = defaultdict(lambda: {
            'topic_name': '',
            'questions': []
        })
        
        for answer in correct_answers:
            q = answer.question
            topic_name = q.topic.name
            
            topic_data[topic_name]['topic_name'] = topic_name
            topic_data[topic_name]['questions'].append({
                'question_id': q.id,
                'question': q.question if q.question else '',
                'options': {
                    'A': q.option_a,
                    'B': q.option_b,
                    'C': q.option_c,
                    'D': q.option_d,
                },
                'correct_answer': q.correct_answer,
                'selected_answer': answer.selected_answer,
                'is_correct': True,
                'time_taken': answer.time_taken or 0
            })
        
        result = []
        for topic_name, data in topic_data.items():
            result.append({
                'topic': topic_name,
                'accuracy': 1.0,
                'no_of_questions': len(data['questions']),
                'avg_time': sum(q['time_taken'] for q in data['questions']) / len(data['questions']) if data['questions'] else 0,
                'questions': data['questions']
            })
        
        print(f"📊 Extracted {len(result)} topics with correct questions for {subject}")
        return {'topics': result}
        
    except Exception as e:
        logger.error(f"Error extracting correct questions for {subject}: {str(e)}")
        return {}


def generate_checkpoints_for_subject(subject: str, topics_data: Dict) -> List[Dict]:
    """
    Generate checkpoints for a subject using LLM.
    
    Args:
        subject: Subject name
        topics_data: Dict with 'topics' array containing topic data
        
    Returns:
        List of checkpoint dicts (exactly 2 items)
    """
    try:
        if not topics_data or not topics_data.get('topics'):
            print(f"⚠️ No topics data provided for {subject}")
            return get_fallback_checkpoints(subject)
        
        topics = topics_data['topics']
        
        # Check if we have wrong/skipped questions or only correct
        has_wrong_or_skipped = any(
            topic.get('questions') and len(topic.get('questions', [])) > 0
            for topic in topics
        )
        
        # Import GeminiClient
        try:
            from ..services.ai.gemini_client import GeminiClient
        except ImportError:
            from neet_app.services.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        if not client.is_available():
            print(f"❌ Gemini client not available for {subject} checkpoints")
            return get_fallback_checkpoints(subject)
        
        # Choose appropriate prompt
        if has_wrong_or_skipped:
            prompt_template = CHECKPOINT_PROMPT
        else:
            prompt_template = CORRECT_UNDERSTANDING_PROMPT
        
        # If we have wrong/skipped questions, send only topics that include those questions.
        # Otherwise (all correct) send the correct-questions topics as-is.
        if has_wrong_or_skipped:
            prompt_topics = [t for t in topics if t.get('questions') and len(t.get('questions', [])) > 0]
        else:
            prompt_topics = topics

        if not prompt_topics:
            print(f"⚠️ No relevant topics to send to LLM for {subject}")
            return get_fallback_checkpoints(subject)

        topics_json = json.dumps(prompt_topics, indent=2)
        prompt = prompt_template.format(
            subject=subject,
            topics_json=topics_json
        )

        logger.info(f"🚀 Using {'CHECKPOINT' if has_wrong_or_skipped else 'CORRECT_UNDERSTANDING'} prompt for {subject} with {len(prompt_topics)} topics")
        
        logger.info(f"🚀 Generating checkpoints for {subject} using {client.model_name}")
        
        # Retry logic: 10 attempts with exponential backoff
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                print(f"🔑 Attempt {attempt}/{max_retries} for {subject}")
                
                # Call LLM
                llm_response = client.generate_response(prompt)
                
                if not llm_response:
                    print(f"❌ Empty response from LLM for {subject} on attempt {attempt}")
                    if attempt < max_retries:
                        import time
                        wait_time = min(2 ** (attempt - 1), 30)  # Exponential backoff, max 30s
                        print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return get_fallback_checkpoints(subject)
                
                # Parse response
                checkpoints = parse_checkpoint_response(llm_response, subject)
                
                # If parsing succeeded, return checkpoints
                if checkpoints is not None:
                    print(f"✅ Checkpoints generated for {subject} on attempt {attempt}")
                    return checkpoints
                
                # Parsing failed, retry
                print(f"⚠️ Parse failed for {subject} on attempt {attempt}, retrying...")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                    
            except BaseException as e:
                logger.error(f"LLM client error for {subject} on attempt {attempt}: {str(e)}")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
        
        # All retries exhausted, use fallback
        print(f"❌ All {max_retries} attempts failed for {subject}, using fallback")
        return get_fallback_checkpoints(subject)
        
    except Exception as e:
        logger.error(f"Error generating checkpoints for {subject}: {str(e)}")
        return get_fallback_checkpoints(subject)


def parse_checkpoint_response(llm_response: str, subject: str) -> List[Dict]:
    """
    Parse LLM response to extract checkpoint array.
    
    Args:
        llm_response: Raw LLM response text
        subject: Subject name (for logging)
        
    Returns:
        List of checkpoint dicts (exactly 2 items)
    """
    try:
        response_text = llm_response.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if len(lines) > 2 else lines)
            response_text = response_text.strip()
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        # Try direct JSON parse
        try:
            checkpoints = json.loads(response_text)
            
            # Validate structure
            if isinstance(checkpoints, list) and len(checkpoints) >= 2:
                # Ensure exactly 2 checkpoints
                checkpoints = checkpoints[:2]
                
                # Validate required fields
                required_fields = ['topic', 'subject', 'subtopic', 'accuracy', 'checklist', 'action_plan', 'citation']
                for cp in checkpoints:
                    if not all(field in cp for field in required_fields):
                        print(f"⚠️ Checkpoint missing required fields for {subject}")
                        return get_fallback_checkpoints(subject)
                    
                    # Ensure citation is a list
                    if not isinstance(cp.get('citation'), list):
                        cp['citation'] = []
                
                print(f"✅ Successfully parsed {len(checkpoints)} checkpoints for {subject}")
                return checkpoints
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error for {subject}: {str(e)}")
            # Return None to trigger retry in calling function
            return None
        
        # If parsing fails, return None to trigger retry
        print(f"⚠️ Could not parse LLM response for {subject}")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing checkpoint response for {subject}: {str(e)}")
        return None


def get_fallback_checkpoints(subject: str) -> List[Dict]:
    """
    Generate fallback checkpoints when LLM is unavailable or fails.
    
    Args:
        subject: Subject name
        
    Returns:
        List of 2 fallback checkpoint dicts
    """
    print(f"⚠️ Using fallback checkpoints for {subject}")
    
    return [
        {
            'topic': subject,
            'subject': subject,
            'subtopic': 'General concepts',
            'accuracy': 0.5,
            'checklist': f'Review {subject} fundamentals to identify weak areas',
            'action_plan': f'Practice {subject} questions systematically from basics',
            'citation': []
        },
        {
            'topic': subject,
            'subject': subject,
            'subtopic': 'Problem-solving',
            'accuracy': 0.5,
            'checklist': f'Strengthen {subject} problem-solving approach',
            'action_plan': f'Solve previous year {subject} questions with time limits',
            'citation': []
        }
    ]


def generate_all_subject_checkpoints(test_session_id: int) -> Dict[str, List[Dict]]:
    """
    Generate checkpoints for all subjects in a test session.
    
    Args:
        test_session_id: ID of the test session
        
    Returns:
        Dict mapping subject names to their checkpoint lists
    """
    try:
        from ..models import TestSession, TestSubjectZoneInsight
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Determine which subjects are present
        subjects_to_process = []
        
        if test_session.physics_topics:
            subjects_to_process.append('Physics')
        if test_session.chemistry_topics:
            subjects_to_process.append('Chemistry')
        if test_session.botany_topics:
            subjects_to_process.append('Botany')
        if test_session.zoology_topics:
            subjects_to_process.append('Zoology')
        if test_session.biology_topics:
            subjects_to_process.append('Biology')
        if test_session.math_topics:
            subjects_to_process.append('Math')
        
        if not subjects_to_process:
            print(f"⚠️ No subjects found in test {test_session_id}")
            return {}
        
        print(f"🎯 Generating checkpoints for test {test_session_id}")
        print(f"📚 Subjects to process: {', '.join(subjects_to_process)}")
        
        results = {}
        
        for subject in subjects_to_process:
            try:
                # Extract wrong/skipped questions
                topics_data = extract_wrong_and_skipped_questions(test_session_id, subject)
                
                # If no wrong/skipped, try correct questions
                if not topics_data or not topics_data.get('topics'):
                    print(f"ℹ️ No wrong/skipped questions for {subject}, checking correct answers")
                    topics_data = extract_correct_questions(test_session_id, subject)
                
                if not topics_data or not topics_data.get('topics'):
                    print(f"⚠️ No questions found for {subject}, skipping")
                    continue
                
                # Generate checkpoints
                checkpoints = generate_checkpoints_for_subject(subject, topics_data)
                
                # Save to database
                insight, created = TestSubjectZoneInsight.objects.update_or_create(
                    test_session_id=test_session_id,
                    subject=subject,
                    defaults={
                        'student_id': test_session.student_id,
                        'checkpoints': checkpoints,
                        'topics_analyzed': topics_data.get('topics', [])
                    }
                )
                
                action = "Created" if created else "Updated"
                print(f"💾 {action} checkpoints for {subject} in test {test_session_id}")
                
                results[subject] = checkpoints
                
            except Exception as e:
                logger.error(f"Error processing {subject} for test {test_session_id}: {str(e)}")
                print(f"❌ Failed to process {subject}: {str(e)}")
                continue
        
        print(f"✅ Checkpoint generation complete for test {test_session_id}")
        print(f"📊 Processed {len(results)}/{len(subjects_to_process)} subjects successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in generate_all_subject_checkpoints for test {test_session_id}: {str(e)}")
        print(f"❌ Failed to generate checkpoints: {str(e)}")
        return {}


"""
Zone Insights Service - Checkpoint-based diagnostic system
Generates subject-wise checkpoints with problem identification and action plans.
"""

import logging
import json
from typing import Dict, List, Optional
from django.db.models import Q

logger = logging.getLogger(__name__)

# LLM Prompt for focus zone generation (wrong/skipped questions)
FOCUS_ZONE_PROMPT = """Task: Generate a focused diagnostic and improvement plan for a NEET student based on their wrong and skipped questions.

Context: You are an AI mentor analyzing the student's mistakes and gaps to provide:
1. What went wrong - Clear identification of the specific misunderstanding or gap
2. How to fix it - Practical, actionable steps to address the issue

Input Data Provided:
- Subject-wise breakdown of wrong and skipped questions
- Each subject contains topics with their wrong/skipped questions
- For each question: question text, options, correct answer, selected answer (if any), and misconception

Your Task:
1. Analyze ALL wrong and skipped questions across all subjects
2. For each subject, identify the 2 most critical issues based on:
   - Frequency of similar mistakes
   - Impact on overall performance
   - Common misconceptions or gaps
3. Generate exactly 2 focus points per subject

Output Format:
For each subject, provide exactly 2 focus points. Each focus point must have:
- Line 1 (What went wrong): Specific identification of the misunderstanding/gap (10-15 words)
- Line 2 (How to fix it): Actionable steps to address it (10-15 words)

Requirements:
- Each line must be 10-15 words maximum
- Use simple, easy-to-understand Indian-English (reading level of a 10-year-old)
- Be specific about the concept/subtopic, not just the topic name
- Action steps must be practical and achievable
- Reference specific concepts from the questions provided

Example (Good):
"Student confused velocity (m/s) with acceleration (m/s²) in motion equations.
Practice 10 motion problems focusing on unit identification and formula selection."

Example (Bad):
"Student weak in Physics.
Study more physics topics."

Important:
- Return ONLY a JSON object with subject names as keys
- Each subject value is an array of exactly 2 strings
- Each string contains both lines separated by a newline character
- No explanations, no notes, no markdown code blocks
- Format: {{"Physics": ["line1\\nline2", "line1\\nline2"], "Chemistry": [...], ...}}

Input Data:
{data_json}
"""

# LLM Prompt for repeated mistakes generation (wrong answers across all platform tests)
REPEATED_MISTAKES_PROMPT = """Task: Identify repeated mistakes across multiple NEET platform tests and provide targeted improvement strategies.

Context: You are an AI mentor analyzing a student's wrong answers from ALL their platform tests to find persistent patterns and misconceptions. Your goal is to:
1. What keeps going wrong - Identify patterns of repeated mistakes across multiple tests
2. How to break the pattern - Provide actionable strategies to overcome these recurring issues

Input Data Provided:
- Subject-wise breakdown of ALL wrong answers from multiple platform tests
- Data grouped by: Subject → Topic → Test → Questions
- For each question: question text, options, correct answer, selected answer, misconception
- Multiple tests allow you to spot recurring patterns

Your Task:
1. Analyze ALL wrong answers across ALL tests and subjects
2. For each subject, identify repeated mistake patterns by:
   - Finding the same type of mistake appearing in multiple tests
   - Identifying persistent misconceptions in specific topics
   - Ranking patterns by frequency and impact
3. For each subject, select the 2 most critical repeated mistake patterns
4. Generate exactly 2 repeated mistake points per subject
5. **IMPORTANT**: For each point, identify the specific TOPIC where the pattern occurs most

Output Format:
For each subject, provide exactly 2 repeated mistake points. Each point must have:
- topic: The specific topic name where this pattern occurs (e.g., "Mechanics", "Redox Reactions")
- line1 (What keeps going wrong): Specific identification of the repeated pattern/misconception (10-15 words)
- line2 (How to break the pattern): Actionable strategy to overcome this recurring issue (10-15 words)

Requirements:
- Each line must be 10-15 words maximum
- Use simple, easy-to-understand Indian-English (reading level of a 10-year-old)
- Focus on PATTERNS across tests, not isolated mistakes
- Be specific about the concept/subtopic causing repeated errors
- Action steps must be practical and achievable
- Reference specific recurring patterns from the data
- Topic name must match one of the topics from the input data

Example (Good):
{{
  "topic": "Mechanics",
  "line1": "Student repeatedly confused velocity with acceleration in 3 tests, mixing units.",
  "line2": "Practice 10 motion problems daily focusing on unit identification and formulas."
}}

Example (Bad):
{{
  "topic": "Physics",
  "line1": "Student made mistakes in Physics.",
  "line2": "Study physics topics better."
}}

Key Focus:
- Look for the SAME type of mistake appearing in MULTIPLE tests
- Prioritize patterns that appear most frequently
- Identify conceptual gaps that persist over time
- Associate each pattern with the specific topic it occurs in

Important:
- Return ONLY a JSON object with subject names as keys
- Each subject value is an array of exactly 2 objects
- Each object must have: "topic", "line1", "line2" fields
- No explanations, no notes, no markdown code blocks
- Format: {{"Physics": [{{"topic": "Mechanics", "line1": "...", "line2": "..."}}, {{"topic": "Thermodynamics", "line1": "...", "line2": "..."}}], "Chemistry": [...], ...}}

Input Data:
{data_json}
"""

# LLM Prompt for checkpoint generation (wrong/skipped questions)
CHECKPOINT_PROMPT = """Task: Generate a comprehensive diagnostic and action plan for a NEET student by identifying both problems AND solutions for their weak topics.
Context: You are an AI mentor helping students understand both:
1. Checklist-WHAT went wrong (diagnostic checklist of problems)
2. Action Plan -HOW to fix it (actionable steps to improve)
For each checkpoint, you will provide BOTH the problem identification (Checklist) AND the corresponding action plan(Action Plan).
Input Data Provided:
- Multiple weak topics with performance metrics (accuracy)
- Wrong questions from each topic including:
  - Question text, options, selected answer, correct answer
  - Misconception   
Your Task:
1. Analyze ALL weak topics and its wrong answers provided.
2. Identify the most critical misunderstanding/misconception done by the student in each topic (diagnostic checklist).
3. The checklist(What went wrong) should be more specific to subtopic or concept and should convey the misconception/misunderstadning clearly instead of just mention concept name or topic name.
    example:
        Bad: Student misunderstood acceleration.
        Good: Student used m/s² as the unit of velocity and applied v = u + at incorrectly, showing confusion between velocity (m/s) and acceleration (m/s²).
4. Each action plan should be directly tied to the specific misunderstanding identified in the checklist and should be practical and achievable for a student to implement.
5. Collect all the possible Checkpoints(checklist and action plan) from given data and Rank the checkpoints by:
   -Severity/Impact: How much this issue affects overall performance
   -Actionability: How clear and achievable the solution is
6. Select ONLY the top 2 most critical checkpoint.
Checkpoint Requirements:
- Each checklist item must be **10-15 words** maximum
- Each action plan item must be **10-15 words** maximum
- Checklist must identify WHAT went wrong (diagnostic, factual) and should be specify the misunderstanding/misconception not just what topic went wrong.
- Action plan must describe HOW to fix that misunderstanding/wrong mental model (prescriptive, actionable)
- Each checkpoints should concentrate on specific subtopic/concept. Don't try to cover multiple issues in one point.
- Use simple, easy-to-understand Indian-English
- Each item should be at the reading level of a 10-year-old Indian student. Use only very simple English words. Do NOT use difficult or formal words.
- Reference the specific topic/subject in context

Citation Requirements:
- Each checkpoint MUST include a "citation" field listing the question numbers that support this insight
- Citation format: array of question numbers, e.g., [5, 12, 18]
- Include 1-5 question numbers per checkpoint as evidence
- Select questions that best demonstrate the specific mastery identified in the checklist
- Questions in citation should be from the correctly answered question data provided for that topic

Guidance (match style in CHECKPOINT_PROMPT):
- Return EXACTLY 2 checkpoint items for THIS SUBJECT (not more, not less)
- Keep each checklist and action_plan tightly focused and paired — the action must directly reinforce the checklist point
- Use supportive tone and concrete next-steps (practice, review examples, solve problems, summarize concepts)
- Ensure checklist and action_plan are short, specific and actionable (10-15 words each)

Important:
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

        # Helper: extract the first JSON array substring (from first '[' to matching ']')
        def _extract_json_array(text: str) -> str:
            start = text.find('[')
            if start == -1:
                return text
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '[':
                    depth += 1
                elif text[i] == ']':
                    depth -= 1
                    if depth == 0:
                        return text[start:i+1]
            # Fallback: return original text if matching bracket not found
            return text

        # Try several parsing strategies, progressively forgiving
        candidates = []
        candidates.append(response_text)
        extracted = _extract_json_array(response_text)
        if extracted and extracted != response_text:
            candidates.insert(0, extracted)

        import ast
        import re

        for candidate in candidates:
            # Try strict JSON first
            try:
                checkpoints = json.loads(candidate)
            except Exception:
                checkpoints = None

            # If JSON parsing failed, try ast.literal_eval after minor token fixes
            if checkpoints is None:
                try:
                    # Convert JSON null/true/false to Python None/True/False for ast
                    py_candidate = candidate.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                    # Try to fix common smart quotes
                    py_candidate = py_candidate.replace('“', '"').replace('”', '"').replace('’', "'")
                    checkpoints = ast.literal_eval(py_candidate)
                except Exception:
                    checkpoints = None

            # If we obtained a Python list-like structure, normalize and validate
            if isinstance(checkpoints, (list, tuple)):
                checkpoints = list(checkpoints)
                if len(checkpoints) >= 2:
                    checkpoints = checkpoints[:2]
                    # Validate required fields
                    required_fields = ['topic', 'subject', 'subtopic', 'accuracy', 'checklist', 'action_plan', 'citation']
                    valid = True
                    for cp in checkpoints:
                        if not isinstance(cp, dict) or not all(field in cp for field in required_fields):
                            valid = False
                            break
                        # Ensure citation is a list
                        if not isinstance(cp.get('citation'), list):
                            cp['citation'] = []
                    if valid:
                        print(f"✅ Successfully parsed {len(checkpoints)} checkpoints for {subject}")
                        return checkpoints

        # If parsing fails for all strategies, log the problematic response for debugging
        print(f"⚠️ Could not parse LLM response for {subject}. Raw response:\n{llm_response[:2000]}")
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
            'citation': [],
            'performanceType': 'weakness'
        },
        {
            'topic': subject,
            'subject': subject,
            'subtopic': 'Problem-solving',
            'accuracy': 0.5,
            'checklist': f'Strengthen {subject} problem-solving approach',
            'action_plan': f'Solve previous year {subject} questions with time limits',
            'citation': [],
            'performanceType': 'weakness'
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

                # Normalize checkpoint keys to a stable schema before saving
                normalized_cp = []
                for cp in (checkpoints or []):
                    ncp = dict(cp)
                    if 'action_plan' in cp and 'actionPlan' not in cp:
                        ncp['actionPlan'] = cp.get('action_plan')
                    if 'performance_type' in cp and 'performanceType' not in cp:
                        ncp['performanceType'] = cp.get('performance_type')
                    # Ensure citation elements are ints where possible
                    if 'citation' in cp and isinstance(cp.get('citation'), list):
                        try:
                            ncp['citation'] = [int(x) for x in cp.get('citation')]
                        except Exception:
                            ncp['citation'] = cp.get('citation')
                    normalized_cp.append(ncp)

                # Compute subject-level aggregates to persist alongside checkpoints
                topics = topics_data.get('topics', []) if topics_data else []
                total_q = sum(int(t.get('no_of_questions', 0)) for t in topics)
                weighted_correct = sum(float(t.get('accuracy', 0)) * int(t.get('no_of_questions', 0)) for t in topics)
                accuracy_val = (weighted_correct / total_q) if total_q else 0.0
                mark_val = weighted_correct
                total_mark_val = float(total_q)
                time_spend_total = sum(float(t.get('avg_time', 0)) * int(t.get('no_of_questions', 0)) for t in topics)
                time_spend_payload = {
                    'total_seconds': round(time_spend_total, 2),
                    'per_topic': [
                        {
                            'topic': t.get('topic'),
                            'avg_time': t.get('avg_time', 0),
                            'no_of_questions': t.get('no_of_questions', 0)
                        }
                        for t in topics
                    ]
                }
                # Identify repeated mistakes (topics with low accuracy)
                repeated = [t.get('topic') for t in topics if float(t.get('accuracy', 0)) < 0.5 and int(t.get('no_of_questions', 0)) > 0]

                # Store per-subject results for aggregation
                results[subject] = {
                    'checkpoints': normalized_cp,
                    'topics_analyzed': topics,
                    'topics_data': topics_data,
                    'accuracy': accuracy_val,
                    'mark': mark_val,
                    'total_mark': total_mark_val,
                    'time_spend': time_spend_payload,
                    'repeated_mistakes': repeated
                }
                
            except Exception as e:
                logger.error(f"Error processing {subject} for test {test_session_id}: {str(e)}")
                print(f"❌ Failed to process {subject}: {str(e)}")
                continue
        
        # Aggregate all subjects into a single row per test
        if results:
            # Build subject_data list from all processed subjects
            subject_data_list = []
            all_checkpoints = []
            all_topics_analyzed = []
            all_repeated_mistakes = []
            
            total_questions = 0
            total_correct = 0
            total_time = 0
            
            for subject, data in results.items():
                # Collect checkpoints from all subjects
                all_checkpoints.extend(data.get('checkpoints', []))
                all_topics_analyzed.extend(data.get('topics_analyzed', []))
                all_repeated_mistakes.extend(data.get('repeated_mistakes', []))
                
                # Build subject entry for subject_data
                topics = data.get('topics_analyzed', [])
                subj_total = sum(int(t.get('no_of_questions', 0)) for t in topics)
                subj_correct = int(data.get('accuracy', 0) * subj_total)
                subj_incorrect = subj_total - subj_correct
                
                subject_data_list.append({
                    'subject_name': subject,
                    'total_questions': subj_total,
                    'correct_answers': subj_correct,
                    'incorrect_answers': subj_incorrect,
                    'skipped_answers': 0,  # Not tracked in checkpoint flow
                    'total_mark': int(data.get('total_mark', 0)),
                    'marks': int(data.get('mark', 0)),
                    'accuracy': round(data.get('accuracy', 0) * 100, 2)
                })
                
                total_questions += subj_total
                total_correct += subj_correct
                total_time += data.get('time_spend', {}).get('total_seconds', 0)
            
            # Calculate overall metrics
            overall_accuracy = (total_correct / total_questions) if total_questions > 0 else 0
            overall_marks = sum(data.get('mark', 0) for data in results.values())
            overall_total_mark = sum(data.get('total_mark', 0) for data in results.values())
            
            # Save single row per test
            TestSubjectZoneInsight.objects.update_or_create(
                test_session_id=test_session_id,
                student_id=test_session.student_id,
                defaults={
                    'student_id': test_session.student_id,
                    'mark': round(overall_marks, 2),
                    'accuracy': round(overall_accuracy, 3),
                    'time_spend': {'total_time_spent': total_time},
                    'total_mark': round(overall_total_mark, 2),
                    'subject_data': subject_data_list,
                    'checkpoints': all_checkpoints,
                    'topics_analyzed': all_topics_analyzed,
                    'repeated_mistake': all_repeated_mistakes,
                    'focus_zone': [],
                    'g_phrase': None,
                }
            )
            print(f"💾 Saved aggregated checkpoints for test {test_session_id}")
        
        print(f"✅ Checkpoint generation complete for test {test_session_id}")
        print(f"📊 Processed {len(results)}/{len(subjects_to_process)} subjects successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in generate_all_subject_checkpoints for test {test_session_id}: {str(e)}")
        print(f"❌ Failed to generate checkpoints: {str(e)}")
        return {}


def compute_and_store_zone_insights(test_session_id: int) -> Dict[str, Dict]:
    """
    Compute and store zone insights metrics for all subjects in a test session.
    Uses new structured calculation logic without LLM checkpoint generation.
    
    Calculates:
    - Total possible marks
    - Accuracy
    - Time spent (JSON format)
    - Marks (based on marking scheme)
    - Subject-wise data (JSON format)
    
    Args:
        test_session_id: ID of the test session
        
    Returns:
        Dict mapping subject names to their metrics
    """
    try:
        print(f"🔄 compute_and_store_zone_insights START for test {test_session_id}")
        from ..models import TestSession, TestAnswer, TestSubjectZoneInsight
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Helper to normalize subject name
        def _normalize_subject(s: str) -> str:
            if not s:
                return 'Other'
            s_low = s.lower()
            if 'physics' in s_low:
                return 'Physics'
            if 'chemistry' in s_low:
                return 'Chemistry'
            if 'botany' in s_low or 'plant' in s_low:
                return 'Botany'
            if 'zoology' in s_low or 'animal' in s_low:
                return 'Zoology'
            if 'biology' in s_low or 'bio' in s_low:
                return 'Biology'
            if 'math' in s_low or 'algebra' in s_low or 'geometry' in s_low:
                return 'Math'
            return s.strip()
        
        # Fetch all answers for this test
        answers = TestAnswer.objects.filter(session_id=test_session_id).select_related('question__topic')
        
        # Group answers by subject
        from collections import defaultdict
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']
        subject_answers = {s: [] for s in subjects}
        
        for answer in answers:
            try:
                topic = answer.question.topic
                subject_name = getattr(topic, 'subject', None)
                normalized = _normalize_subject(subject_name) if subject_name else None
                if normalized in subjects:
                    subject_answers[normalized].append(answer)
            except Exception:
                continue
        
        results = {}
        subject_data_list = []
        
        for subject in subjects:
            subject_ans = subject_answers[subject]
            if not subject_ans:
                continue
            
            # Subject calculations
            subj_total = len(subject_ans)
            subj_correct = sum(1 for a in subject_ans if a.is_correct)
            subj_incorrect = sum(1 for a in subject_ans if a.selected_answer and not a.is_correct)
            subj_skipped = sum(1 for a in subject_ans if not a.selected_answer)
            subj_total_mark = subj_total * 4
            subj_marks = (subj_correct * 4) - (subj_incorrect * 1)
            subj_accuracy = (subj_correct / subj_total * 100) if subj_total > 0 else 0
            
            # Subject time spent
            subj_correct_time = sum(a.time_taken or 0 for a in subject_ans if a.is_correct)
            subj_incorrect_time = sum(a.time_taken or 0 for a in subject_ans if a.selected_answer and not a.is_correct)
            subj_skipped_time = sum(a.time_taken or 0 for a in subject_ans if not a.selected_answer)
            subj_total_time = subj_correct_time + subj_incorrect_time + subj_skipped_time
            
            subj_time_json = {
                "total_time_spent": subj_total_time,
                "correct_time_spent": subj_correct_time,
                "incorrect_time_spent": subj_incorrect_time,
                "skipped_time_spent": subj_skipped_time
            }
            
            # Subject-wise data entry
            subject_data_entry = {
                "subject_name": subject,
                "total_questions": subj_total,
                "correct_answers": subj_correct,
                "incorrect_answers": subj_incorrect,
                "skipped_answers": subj_skipped,
                "total_mark": subj_total_mark,
                "marks": subj_marks,
                "accuracy": round(subj_accuracy, 2)
            }            
            subject_data_list.append(subject_data_entry)
            
            results[subject] = {
                'mark': subj_marks,
                'accuracy': round(subj_accuracy, 2),
                'total_mark': subj_total_mark,
                'time_spend': subj_time_json,
                'subject_data': subject_data_entry
            }
            
            logger.info(f"Prepared zone insights for {subject} in test {test_session_id}")
        
        
        # Compute overall aggregates and persist a single per-test row
        total_questions = answers.count()
        total_correct = sum(1 for a in answers if a.is_correct)
        total_incorrect = sum(1 for a in answers if a.selected_answer and not a.is_correct)
        total_skipped = sum(1 for a in answers if not a.selected_answer)
        
        total_possible_marks = total_questions * 4
        total_marks = (total_correct * 4) - (total_incorrect * 1)
        
        correct_time = sum(a.time_taken or 0 for a in answers if a.is_correct)
        incorrect_time = sum(a.time_taken or 0 for a in answers if a.selected_answer and not a.is_correct)
        skipped_time = sum(a.time_taken or 0 for a in answers if not a.selected_answer)
        total_time = correct_time + incorrect_time + skipped_time
        
        time_spend_payload = {
            "total_time_spent": total_time,
            "correct_time_spent": correct_time,
            "incorrect_time_spent": incorrect_time,
            "skipped_time_spent": skipped_time
        }
        
        overall_accuracy_fraction = round(((total_correct / total_questions) if total_questions > 0 else 0), 3)
        
        # Prepare g_phrase: only for platform tests. For custom tests keep None.
        g_phrase_val = None
        try:
            # Only generate phrase for platform tests
            if getattr(test_session, 'test_type', None) == 'platform':
                # Find the most recent previous platform test for this student (exclude current)
                prev_sessions = TestSession.objects.filter(
                    student_id=test_session.student_id,
                    test_type='platform',
                    is_completed=True
                ).exclude(id=test_session_id).order_by('-end_time')

                prev_session = prev_sessions.first() if prev_sessions.exists() else None

                if not prev_session:
                    # First platform test for this student: use a welcoming phrase
                    try:
                        student_name = ''
                        from ..models import StudentProfile
                        sp = StudentProfile.objects.filter(student_id=test_session.student_id).first()
                        if sp and getattr(sp, 'full_name', None):
                            student_name = sp.full_name
                    except Exception:
                        student_name = ''

                    g_phrase_val = "Future Doctor {name}, your dedication today builds tomorrow's white coat.".format(name=student_name or '')

                if prev_session:
                    # Get the previous insight row (if any) for that session and same student
                    prev_insight = TestSubjectZoneInsight.objects.filter(
                        test_session__id=prev_session.id,
                        student__student_id=test_session.student_id
                    ).order_by('-created_at').first()

                    if not prev_insight or prev_insight.accuracy is None:
                        # No previous insight available — fall back to the welcoming phrase
                        try:
                            student_name = ''
                            from ..models import StudentProfile
                            sp = StudentProfile.objects.filter(student_id=test_session.student_id).first()
                            if sp and getattr(sp, 'full_name', None):
                                student_name = sp.full_name
                        except Exception:
                            student_name = ''
                        g_phrase_val = "Future Doctor {name}, your dedication today builds tomorrow's white coat.".format(name=student_name or '')

                    if prev_insight and prev_insight.accuracy is not None:
                        prev_acc_frac = float(prev_insight.accuracy)  # stored as 0-1 fraction
                        curr_acc_frac = float(overall_accuracy_fraction)
                        diff_pct = round((curr_acc_frac - prev_acc_frac) * 100.0, 2)

                        # If there is no change since previous test, use the static encouragement phrase
                        if diff_pct == 0:
                            try:
                                student_name = ''
                                from ..models import StudentProfile
                                sp = StudentProfile.objects.filter(student_id=test_session.student_id).first()
                                if sp and getattr(sp, 'full_name', None):
                                    student_name = sp.full_name
                            except Exception:
                                student_name = ''

                            g_phrase_val = "Future Doctor {name}, your dedication today builds tomorrow's white coat.".format(name=student_name or '')
                        # Only proceed when there's a non-zero change
                        if diff_pct != 0:
                            # Candidate phrase pools
                            improvement_phrases = [
                                'Future Doctor {name}, you just boosted accuracy by {change}% — outstanding progress!',
                                '{name}, a powerful {change}% jump! Your NEET rank dream is getting closer.',
                                'Dr. {name}, {change}% improvement proves your dedication is paying off.',
                                '{name}, you climbed {change}% higher — thats true topper energy!',
                                'Champion {name}, {change}% growth shows your concepts are sharpening beautifully.',
                                '{name}, {change}% stronger today — success loves this consistency.',
                                'Brilliant move, {name}! {change}% rise shows unstoppable preparation power.',
                                '{name}, that {change}% gain is a big step toward medical college.',
                                'Dr. {name}, {change}% improvement reflects smarter strategy and stronger focus.',
                                '{name}, your {change}% accuracy boost screams future NEET ranker!'
                            ]

                            drop_phrases = [
                                'Future Doctor {name}, {change}% dip today — comeback loading stronger.',
                                '{name}, a {change}% drop is temporary; your goal is permanent.',
                                'Dr. {name}, even toppers face dips — rise beyond this {change}%.',
                                '{name}, {change}% setback today builds tomorrows powerful breakthrough.',
                                'Stay calm, {name}. This {change}% fall is fuel for growth.',
                                'Champion {name}, {change}% down now — next test, double focus.',
                                '{name}, every {change}% mistake teaches winning strategies.',
                                'Dr. {name}, {change}% lower today, but your ambition stays higher.',
                                '{name}, small {change}% dip — big determination ahead.',
                                'Future Ranker {name}, {change}% drop means refine, reset, rise.'
                            ]

                            import random

                            # Exclude g_phrases used in previous 3 insights for this student
                            recent_phrases_qs = TestSubjectZoneInsight.objects.filter(
                                student__student_id=test_session.student_id
                            ).exclude(test_session__id=test_session_id).exclude(g_phrase__isnull=True).exclude(g_phrase__exact='').order_by('-created_at')[:3]

                            recent_phrases = set(p.g_phrase for p in recent_phrases_qs if p.g_phrase)

                            pool = improvement_phrases if diff_pct > 0 else drop_phrases
                            # Exclude recently used phrases
                            remaining = [p for p in pool if p not in recent_phrases]
                            if not remaining:
                                remaining = pool

                            chosen = random.choice(remaining)

                            # Student name lookup
                            student_name = ''
                            try:
                                from ..models import StudentProfile
                                sp = StudentProfile.objects.filter(student_id=test_session.student_id).first()
                                if sp and getattr(sp, 'full_name', None):
                                    student_name = sp.full_name
                            except Exception:
                                student_name = ''

                            # Format change value: show absolute magnitude without negative sign
                            change_val = abs(diff_pct)
                            # Remove trailing .0 when possible
                            if float(change_val).is_integer():
                                change_str = str(int(change_val))
                            else:
                                change_str = str(change_val)

                            # Build final phrase
                            g_phrase_val = chosen.format(name=student_name or '', change=change_str)

        except Exception as _gp_exc:
            # Be defensive: never fail insight storing due to g_phrase generation
            logger.error(f'g_phrase generation failed for session {test_session_id}: {_gp_exc}')
            g_phrase_val = None
        
        # Store single row per test with all subjects in subject_data
        TestSubjectZoneInsight.objects.update_or_create(
            test_session_id=test_session_id,
            student_id=test_session.student_id,
            defaults={
                'student_id': test_session.student_id,
                'mark': total_marks,
                'accuracy': overall_accuracy_fraction,
                'time_spend': time_spend_payload,
                'total_mark': total_possible_marks,
                'subject_data': subject_data_list,
                'focus_zone': [],
                'repeated_mistake': [],
                'g_phrase': g_phrase_val,
                'checkpoints': [],
                'topics_analyzed': []
            }
        )
        
        logger.info(f"✅ Zone insights computation complete for test {test_session_id}")
        logger.info(f"📊 Processed {len(results)} subjects successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in compute_and_store_zone_insights for test {test_session_id}: {str(e)}")
        return {}


def extract_focus_zone_data(test_session_id: int) -> Dict:
    """
    Extract wrong and skipped questions for focus zone generation.
    Groups by subject -> topic -> questions with full metadata.
    Only includes skipped questions if time_taken > 5 seconds.
    
    Args:
        test_session_id: ID of the test session
        
    Returns:
        Dict with structure:
        {
            "Physics": {
                "topics": [
                    {
                        "topic_name": "Mechanics",
                        "questions": [
                            {
                                "question_id": 123,
                                "question": "A ball is thrown...",
                                "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
                                "correct_answer": "C",
                                "selected_answer": "A",
                                "misconception": "Confused velocity with acceleration"
                            },
                            ...
                        ]
                    },
                    ...
                ]
            },
            "Chemistry": {...},
            ...
        }
    """
    try:
        from ..models import TestSession, TestAnswer, Topic
        from collections import defaultdict
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Define subjects to process
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']
        subject_map = {
            'Physics': test_session.physics_topics,
            'Chemistry': test_session.chemistry_topics,
            'Botany': test_session.botany_topics,
            'Zoology': test_session.zoology_topics,
            'Biology': test_session.biology_topics,
            'Math': test_session.math_topics
        }
        
        result = {}
        
        for subject in subjects:
            topic_names = subject_map.get(subject, [])
            
            if not topic_names:
                continue
            
            # Convert topic names to IDs
            topic_objects = Topic.objects.filter(name__in=topic_names)
            topic_ids = list(topic_objects.values_list('id', flat=True))
            
            if not topic_ids:
                continue
            
            # Get all answers for these topics
            answers = TestAnswer.objects.filter(
                session_id=test_session_id,
                question__topic_id__in=topic_ids
            ).select_related('question', 'question__topic').order_by('id')
            
            # Group by topic
            topic_data = defaultdict(list)
            
            for answer in answers:
                # Filter: only wrong or skipped (with time > 5s)
                is_wrong = answer.selected_answer and not answer.is_correct
                is_skipped_with_time = (
                    not answer.selected_answer and 
                    (answer.time_taken or 0) > 5
                )
                
                if not (is_wrong or is_skipped_with_time):
                    continue
                
                q = answer.question
                topic_name = q.topic.name
                
                # Extract misconception for wrong answers
                misconception_text = None
                if is_wrong and answer.selected_answer:
                    misconceptions = q.misconceptions or {}
                    selected_option = answer.selected_answer.upper()
                    misconception_text = misconceptions.get(f"option_{selected_option.lower()}", None)
                
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
                    'misconception': misconception_text
                }
                
                topic_data[topic_name].append(question_entry)
            
            # Structure by topics
            if topic_data:
                topics_list = []
                for topic_name, questions in topic_data.items():
                    topics_list.append({
                        'topic_name': topic_name,
                        'questions': questions
                    })
                
                result[subject] = {
                    'topics': topics_list
                }
        
        logger.info(f"📊 Extracted focus zone data for {len(result)} subjects in test {test_session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting focus zone data for test {test_session_id}: {str(e)}")
        return {}


def generate_focus_zone(test_session_id: int) -> Dict:
    """
    Generate focus zone data using LLM.
    Analyzes wrong and skipped questions to provide subject-wise focus points.
    Each subject gets exactly 2 focus points with "what went wrong" and "how to fix it".
    
    Args:
        test_session_id: ID of the test session
        
    Returns:
        Dict with structure:
        {
            "Physics": [
                "Student confused velocity with acceleration in motion equations.\\nPractice 10 motion problems focusing on unit identification.",
                "..."
            ],
            "Chemistry": [...],
            ...
        }
    """
    try:
        print(f"🎯 generate_focus_zone START for test {test_session_id}")
        from ..models import TestSession, TestSubjectZoneInsight
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        # Extract wrong and skipped questions
        focus_data = extract_focus_zone_data(test_session_id)
        
        if not focus_data:
            logger.warning(f"No focus zone data extracted for test {test_session_id}")
            return {}
        
        # Import GeminiClient
        try:
            from ..services.ai.gemini_client import GeminiClient
        except ImportError:
            from neet_app.services.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        if not client.is_available():
            logger.error(f"❌ Gemini client not available for focus zone generation")
            return {}
        
        # Prepare prompt
        data_json = json.dumps(focus_data, indent=2)
        prompt = FOCUS_ZONE_PROMPT.format(data_json=data_json)
        
        logger.info(f"🚀 Generating focus zone for test {test_session_id} using {client.model_name}")
        
        # Retry logic: 10 attempts with exponential backoff
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                print(f"🔑 Focus zone generation attempt {attempt}/{max_retries}")
                
                # Call LLM
                llm_response = client.generate_response(prompt)
                
                if not llm_response:
                    print(f"❌ Empty response from LLM on attempt {attempt}")
                    if attempt < max_retries:
                        import time
                        wait_time = min(2 ** (attempt - 1), 30)
                        print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return {}
                
                # Parse response
                focus_zone_data = parse_focus_zone_response(llm_response)
                
                if focus_zone_data is not None:
                    print(f"✅ Focus zone generated on attempt {attempt}")
                    
                    # Update the TestSubjectZoneInsight record
                    insight = TestSubjectZoneInsight.objects.filter(
                        test_session_id=test_session_id,
                        student_id=test_session.student_id
                    ).first()
                    
                    if insight:
                        insight.focus_zone = focus_zone_data
                        insight.save(update_fields=['focus_zone'])
                        logger.info(f"💾 Updated focus_zone for test {test_session_id}")
                    else:
                        logger.warning(f"⚠️ No TestSubjectZoneInsight found for test {test_session_id}")
                    
                    return focus_zone_data
                
                # Parsing failed, retry
                print(f"⚠️ Parse failed on attempt {attempt}, retrying...")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.error(f"LLM client error on attempt {attempt}: {str(e)}")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
        
        # All retries exhausted
        print(f"❌ All {max_retries} attempts failed for focus zone generation")
        return {}
        
    except Exception as e:
        logger.error(f"Error generating focus zone for test {test_session_id}: {str(e)}")
        return {}


def parse_focus_zone_response(llm_response: str) -> Optional[Dict]:
    """
    Parse LLM response to extract focus zone data.
    Expected format: {"Physics": ["point1", "point2"], "Chemistry": [...], ...}
    
    Args:
        llm_response: Raw LLM response text
        
    Returns:
        Dict mapping subject names to arrays of 2 focus point strings, or None if parsing fails
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
        
        # Try JSON parsing
        try:
            focus_zone_data = json.loads(response_text)
        except Exception:
            # Try ast.literal_eval as fallback
            import ast
            try:
                py_text = response_text.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                focus_zone_data = ast.literal_eval(py_text)
            except Exception:
                print(f"⚠️ Could not parse focus zone response:\n{llm_response[:500]}")
                return None
        
        # Validate structure
        if not isinstance(focus_zone_data, dict):
            print(f"⚠️ Focus zone response is not a dict")
            return None
        
        # Validate each subject has exactly 2 points
        for subject, points in focus_zone_data.items():
            if not isinstance(points, list):
                print(f"⚠️ Subject {subject} points is not a list")
                return None
            if len(points) != 2:
                print(f"⚠️ Subject {subject} has {len(points)} points, expected 2")
                # Truncate or pad to 2 points
                if len(points) > 2:
                    focus_zone_data[subject] = points[:2]
                elif len(points) < 2:
                    # Pad with placeholder if less than 2
                    while len(focus_zone_data[subject]) < 2:
                        focus_zone_data[subject].append("Review fundamental concepts carefully.\nPractice more questions from this subject.")
        
        print(f"✅ Successfully parsed focus zone for {len(focus_zone_data)} subjects")
        return focus_zone_data
        
    except Exception as e:
        logger.error(f"Error parsing focus zone response: {str(e)}")
        return None


def parse_repeated_mistakes_response(llm_response: str) -> Optional[Dict]:
    """
    Parse LLM response to extract repeated mistakes data with topic information.
    Expected format: {"Physics": [{"topic": "Mechanics", "line1": "...", "line2": "..."}, ...], ...}

    Parsing is multi-strategy and resilient:
    1. Strip markdown fences.
    2. Try strict json.loads on full text.
    3. If that fails, bracket-match to extract the outermost {...} JSON object.
    4. If that fails, fall back to ast.literal_eval.
    5. Normalise: truncate/pad each subject list to exactly 2 items;
       fill in missing 'topic' or coerce non-dict points transparently.
    6. On any parse failure, log the first 1000 chars of the raw response for debugging.
    """
    import ast

    def _extract_json_object(text: str) -> str:
        """Return the substring spanning the first top-level {...} block."""
        start = text.find('{')
        if start == -1:
            return text
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return text  # unmatched — return original

    try:
        response_text = llm_response.strip()

        # ── 1. Strip markdown code fences ─────────────────────────────────────
        if response_text.startswith('```'):
            lines_parts = response_text.split('\n')
            response_text = '\n'.join(lines_parts[1:-1] if len(lines_parts) > 2 else lines_parts)
            response_text = response_text.strip()
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()

        # ── 2-4. Multi-strategy parsing ────────────────────────────────────────
        repeated_data = None

        candidates = [response_text]
        extracted = _extract_json_object(response_text)
        if extracted and extracted != response_text:
            candidates.insert(0, extracted)  # try bracket-extracted first

        for candidate in candidates:
            # strict JSON
            try:
                repeated_data = json.loads(candidate)
                if repeated_data is not None:
                    break
            except Exception:
                pass

            # ast fallback
            try:
                py_text = candidate.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                py_text = py_text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
                repeated_data = ast.literal_eval(py_text)
                if repeated_data is not None:
                    break
            except Exception:
                pass

        if repeated_data is None:
            print(f"⚠️ Could not parse repeated mistakes response (all strategies failed).\n"
                  f"RAW (first 1000 chars): {llm_response[:1000]}")
            return None

        # ── 5. Validate + normalise ────────────────────────────────────────────
        if not isinstance(repeated_data, dict):
            print(f"⚠️ Repeated mistakes response is not a dict (got {type(repeated_data).__name__}).\n"
                  f"RAW: {llm_response[:500]}")
            return None

        _PLACEHOLDER = {
            "topic": "General",
            "line1": "Review fundamental concepts carefully.",
            "line2": "Practice more questions from this subject."
        }

        for subject in list(repeated_data.keys()):
            points = repeated_data[subject]

            # Points must be a list
            if not isinstance(points, list):
                print(f"⚠️ Subject '{subject}' value is not a list — skipping subject")
                repeated_data.pop(subject)
                continue

            # Truncate or pad to exactly 2
            if len(points) > 2:
                print(f"⚠️ Subject '{subject}' has {len(points)} points — truncating to 2")
                repeated_data[subject] = points[:2]
            elif len(points) < 2:
                print(f"⚠️ Subject '{subject}' has {len(points)} points — padding to 2")
                while len(repeated_data[subject]) < 2:
                    repeated_data[subject].append(dict(_PLACEHOLDER))

            # Validate / repair each point
            for i, point in enumerate(repeated_data[subject]):
                if not isinstance(point, dict):
                    print(f"⚠️ Subject '{subject}' point {i} is not a dict — replacing with placeholder")
                    repeated_data[subject][i] = dict(_PLACEHOLDER)
                    continue

                if 'topic' not in point or not point['topic']:
                    point['topic'] = 'General'

                # line1 / line2 are mandatory
                if 'line1' not in point or 'line2' not in point:
                    missing = [k for k in ('line1', 'line2') if k not in point]
                    print(f"⚠️ Subject '{subject}' point {i} missing fields {missing} — replacing with placeholder")
                    repeated_data[subject][i] = dict(_PLACEHOLDER)

        if not repeated_data:
            print("⚠️ Repeated mistakes dict is empty after normalisation")
            return None

        print(f"✅ Successfully parsed repeated mistakes for {len(repeated_data)} subjects: {list(repeated_data.keys())}")
        return repeated_data

    except Exception as e:
        logger.error(f"Error parsing repeated mistakes response: {str(e)}\n"
                     f"RAW (first 1000 chars): {llm_response[:1000]}")
        return None


def extract_repeated_mistakes_data(student_id: str) -> Dict:
    """
    Extract wrong answers from ALL platform tests for a student.
    Groups by subject → topic → test → questions.
    
    Args:
        student_id: Student's ID
        
    Returns:
        Dict with structure:
        {
            "Physics": {
                "topics": [
                    {
                        "topic_name": "Mechanics",
                        "tests": [
                            {
                                "test_name": "NEET 2024 Mock 1",
                                "test_id": 101,
                                "questions": [
                                    {
                                        "question_id": 123,
                                        "question": "A ball is thrown...",
                                        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
                                        "correct_answer": "C",
                                        "selected_answer": "A",
                                        "misconception": "Confused velocity with acceleration"
                                    },
                                    ...
                                ]
                            },
                            ...
                        ]
                    },
                    ...
                ]
            },
            "Chemistry": {...},
            ...
        }
    """
    try:
        from ..models import TestSession, TestAnswer, Topic, PlatformTest
        from collections import defaultdict
        
        # Get all completed platform tests for this student
        platform_tests = TestSession.objects.filter(
            student_id=student_id,
            test_type='platform',
            is_completed=True
        ).order_by('-end_time')
        
        if not platform_tests.exists():
            logger.warning(f"No completed platform tests found for student {student_id}")
            return {}
        
        logger.info(f"📊 Found {platform_tests.count()} platform tests for student {student_id}")
        
        # Define subjects to process
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']
        result = {}
        
        for subject in subjects:
            # Structure: topic_name -> test_id -> questions list
            topic_test_data = defaultdict(lambda: defaultdict(list))
            
            for test_session in platform_tests:
                # Get subject-specific topic names for this test
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
                    continue
                
                # Convert topic names to IDs
                topic_objects = Topic.objects.filter(name__in=topic_names)
                topic_ids = list(topic_objects.values_list('id', flat=True))
                
                if not topic_ids:
                    continue
                
                # Get ONLY wrong answers for these topics in this test
                wrong_answers = TestAnswer.objects.filter(
                    session_id=test_session.id,
                    question__topic_id__in=topic_ids,
                    selected_answer__isnull=False,  # Must have selected an answer
                    is_correct=False  # Wrong answer
                ).select_related('question', 'question__topic').order_by('id')
                
                # Get test name
                if test_session.platform_test:
                    test_name = test_session.platform_test.test_name
                else:
                    test_name = f"Test #{test_session.id}"
                
                # Group by topic
                for answer in wrong_answers:
                    q = answer.question
                    topic_name = q.topic.name
                    
                    # Extract misconception
                    misconception_text = None
                    if answer.selected_answer:
                        misconceptions = q.misconceptions or {}
                        selected_option = answer.selected_answer.upper()
                        misconception_text = misconceptions.get(f"option_{selected_option.lower()}", None)
                    
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
                        'misconception': misconception_text
                    }
                    
                    topic_test_data[topic_name][test_session.id].append(question_entry)
            
            # Structure the data for LLM
            if topic_test_data:
                topics_list = []
                for topic_name, tests_dict in topic_test_data.items():
                    tests_list = []
                    for test_id, questions in tests_dict.items():
                        # Get test name
                        test_session = TestSession.objects.get(id=test_id)
                        if test_session.platform_test:
                            test_name = test_session.platform_test.test_name
                        else:
                            test_name = f"Test #{test_id}"
                        
                        tests_list.append({
                            'test_name': test_name,
                            'test_id': test_id,
                            'questions': questions
                        })
                    
                    topics_list.append({
                        'topic_name': topic_name,
                        'tests': tests_list
                    })
                
                result[subject] = {
                    'topics': topics_list
                }
        
        logger.info(f"📊 Extracted repeated mistakes data for {len(result)} subjects")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting repeated mistakes data for student {student_id}: {str(e)}")
        return {}


def generate_repeated_mistakes(student_id: str, test_session_id: int) -> Dict:
    """
    Generate repeated mistakes data using LLM.
    Analyzes wrong answers from all platform tests to identify recurring patterns.
    Each subject gets exactly 2 repeated mistake points with "what keeps going wrong" and "how to break the pattern".
    
    Args:
        student_id: Student's ID
        test_session_id: Current test session ID (for updating the insight record)
        
    Returns:
        Dict with structure:
        {
            "Physics": [
                "Student repeatedly confused velocity with acceleration in 3 tests.\\nPractice 10 motion problems daily focusing on units.",
                "..."
            ],
            "Chemistry": [...],
            ...
        }
    """
    try:
        print(f"🔁 generate_repeated_mistakes START for student {student_id} / session {test_session_id}")
        from ..models import TestSession, TestSubjectZoneInsight
        
        # Extract wrong answers from all platform tests
        repeated_data = extract_repeated_mistakes_data(student_id)
        
        if not repeated_data:
            logger.warning(f"No repeated mistakes data extracted for student {student_id}")
            return {}
        
        # Import GeminiClient
        try:
            from ..services.ai.gemini_client import GeminiClient
        except ImportError:
            from neet_app.services.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        if not client.is_available():
            logger.error(f"❌ Gemini client not available for repeated mistakes generation")
            return {}
        
        # Prepare prompt
        data_json = json.dumps(repeated_data, indent=2)
        prompt = REPEATED_MISTAKES_PROMPT.format(data_json=data_json)
        
        logger.info(f"🚀 Generating repeated mistakes for student {student_id} using {client.model_name}")
        
        # Retry logic: 10 attempts with exponential backoff
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                print(f"🔑 Repeated mistakes generation attempt {attempt}/{max_retries}")
                
                # Call LLM
                llm_response = client.generate_response(prompt)
                
                if not llm_response:
                    print(f"❌ Empty response from LLM on attempt {attempt}")
                    if attempt < max_retries:
                        import time
                        wait_time = min(2 ** (attempt - 1), 30)
                        print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return {}
                
                # Parse response using repeated mistakes parser (handles topic structure)
                repeated_mistakes_data = parse_repeated_mistakes_response(llm_response)
                
                if repeated_mistakes_data is not None:
                    print(f"✅ Repeated mistakes generated on attempt {attempt}")
                    
                    # Update the TestSubjectZoneInsight record
                    insight = TestSubjectZoneInsight.objects.filter(
                        test_session_id=test_session_id,
                        student_id=student_id
                    ).first()
                    
                    if insight:
                        insight.repeated_mistake = repeated_mistakes_data
                        insight.save(update_fields=['repeated_mistake'])
                        logger.info(f"💾 Updated repeated_mistake for test {test_session_id}")
                    else:
                        logger.warning(f"⚠️ No TestSubjectZoneInsight found for test {test_session_id}")
                    
                    return repeated_mistakes_data
                
                # Parsing failed, retry
                print(f"⚠️ Parse failed on attempt {attempt}, retrying...")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.error(f"LLM client error on attempt {attempt}: {str(e)}")
                if attempt < max_retries:
                    import time
                    wait_time = min(2 ** (attempt - 1), 30)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
        
        # All retries exhausted
        print(f"❌ All {max_retries} attempts failed for repeated mistakes generation")
        return {}
        
    except Exception as e:
        logger.error(f"Error generating repeated mistakes for student {student_id}: {str(e)}")
        return {}


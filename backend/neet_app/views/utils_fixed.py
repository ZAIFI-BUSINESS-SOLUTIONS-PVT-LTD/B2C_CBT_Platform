from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from neomodel import db
from ..models import Topic, Question, TestSession, TestAnswer, StudentProfile
import logging
from django.db import transaction, IntegrityError
import random
import re

logger = logging.getLogger(__name__)


def clean_mathematical_text(text):
    """
    Clean mathematical expressions and LaTeX formatting from text.
    Handles common patterns found in question databases.
    
    Args:
        text (str): Raw text with potential LaTeX/regex formatting
        
    Returns:
        str: Cleaned text with mathematical expressions converted to readable format
    """
    if not text or not isinstance(text, str):
        return text
    
    # Store original for logging if needed
    original_text = text
    
    try:
        # Remove LaTeX document structure commands
        text = re.sub(r'\\documentclass.*?\\begin\{document\}', '', text, flags=re.DOTALL)
        text = re.sub(r'\\end\{document\}', '', text)
        
        # Handle display math delimiters $$...$$ FIRST (before single $)
        text = re.sub(r'\$\$([^$]+)\$\$', r'\1', text)
        
        # Handle inline math: $...$ -> keep content but remove $ 
        text = re.sub(r'\$([^$]+)\$', r'\1', text)
        
        # Remove display math delimiters
        text = re.sub(r'\\\[', '', text)
        text = re.sub(r'\\\]', '', text)
        
        # Handle mathematical expressions
        # Convert LaTeX fractions: \frac{a}{b} -> (a/b)
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1/\2)', text)
        
        # Convert LaTeX square roots: \sqrt{x} -> √(x)
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', text)
        
        # Clean up common LaTeX commands BEFORE handling subscripts/superscripts
        text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)  # \text{abc} -> abc
        text = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', text)  # \mathrm{abc} -> abc
        text = re.sub(r'\\mathbf\{([^}]+)\}', r'\1', text)  # \mathbf{abc} -> abc
        text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)  # \textbf{abc} -> abc
        text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)  # \emph{abc} -> abc
        
        # Handle superscripts: ^{2} or ^2 -> ²
        superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
        text = re.sub(r'\^\{([0-9]+)\}', lambda m: ''.join(superscript_map.get(d, d) for d in m.group(1)), text)
        text = re.sub(r'\^([0-9])', lambda m: superscript_map.get(m.group(1), m.group(1)), text)
        
        # Handle subscripts: _{2} or _2 -> ₂
        subscript_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'}
        text = re.sub(r'_\{([0-9]+)\}', lambda m: ''.join(subscript_map.get(d, d) for d in m.group(1)), text)
        text = re.sub(r'_([0-9])', lambda m: subscript_map.get(m.group(1), m.group(1)), text)
        
        # Convert common LaTeX symbols to Unicode
        symbol_replacements = {
            r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ', r'\\delta': 'δ',
            r'\\epsilon': 'ε', r'\\theta': 'θ', r'\\lambda': 'λ', r'\\mu': 'μ',
            r'\\pi': 'π', r'\\sigma': 'σ', r'\\tau': 'τ', r'\\phi': 'φ',
            r'\\omega': 'ω', r'\\Delta': 'Δ', r'\\Omega': 'Ω',
            r'\\times': '×', r'\\div': '÷', r'\\pm': '±', r'\\mp': '∓',
            r'\\leq': '≤', r'\\geq': '≥', r'\\neq': '≠', r'\\approx': '≈',
            r'\\infty': '∞', r'\\sum': '∑', r'\\prod': '∏', r'\\int': '∫',
            r'\\partial': '∂', r'\\nabla': '∇', r'\\degree': '°',
            r'\\cdot': '·', r'\\bullet': '•'
        }
        
        for latex_symbol, unicode_symbol in symbol_replacements.items():
            text = re.sub(latex_symbol, unicode_symbol, text)
        
        # Handle mathematical environments
        # Remove \begin{equation} and \end{equation}
        text = re.sub(r'\\begin\{equation\*?\}', '', text)
        text = re.sub(r'\\end\{equation\*?\}', '', text)
        text = re.sub(r'\\begin\{align\*?\}', '', text)
        text = re.sub(r'\\end\{align\*?\}', '', text)
        
        # Remove remaining LaTeX commands (backslash followed by word)
        text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
        
        # Clean up braces and brackets - do this in multiple passes for nested braces
        # First pass: simple braces
        text = re.sub(r'\{([^{}]*)\}', r'\1', text)
        # Second pass: any remaining braces
        text = re.sub(r'\{([^{}]*)\}', r'\1', text)
        # Third pass: clean up any remaining empty braces
        text = re.sub(r'\{\}', '', text)
        
        # Handle special patterns like T^{2}=Kr^{3} (if any remain after previous cleaning)
        text = re.sub(r'([A-Za-z])\^\{([0-9]+)\}', lambda m: f"{m.group(1)}{superscript_map.get(m.group(2), m.group(2))}", text)
        
        # Clean up multiple spaces and whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove any remaining backslashes that aren't part of valid escape sequences
        text = re.sub(r'\\(?![nrtbf\'\"\\])', '', text)
        
        return text
        
    except Exception as e:
        logger.warning(f"Error cleaning mathematical text: {e}. Original: {original_text[:100]}...")
        # Return original text if cleaning fails
        return original_text


def generate_questions_for_topics(selected_topics, question_count=None):
    """
    Generate questions for the selected topics with cleaned mathematical expressions.
    
    Args:
        selected_topics: List of topic IDs
        question_count: Maximum number of questions to return (optional)
    
    Returns:
        QuerySet of Question objects with cleaned text
    """
    try:
        # Get all questions for the selected topics
        questions = Question.objects.filter(topic_id__in=selected_topics)
        
        # If question_count is specified and we have more questions than needed,
        # randomly select the specified number
        if question_count and questions.count() > question_count:
            # Convert to list, shuffle, and take the first N
            questions_list = list(questions)
            random.shuffle(questions_list)
            # Return a queryset-like structure
            question_ids = [q.id for q in questions_list[:question_count]]
            questions = Question.objects.filter(id__in=question_ids)
        
        # Clean mathematical expressions in questions if they haven't been cleaned yet
        for question in questions:
            # Check if question text contains LaTeX patterns
            if any(pattern in question.question for pattern in ['\\', '$', '^{', '_{', '\\frac']):
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d'])
        
        logger.info(f"Generated {questions.count()} questions for topics {selected_topics}")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions for topics {selected_topics}: {str(e)}")
        # Return empty queryset if there's an error
        return Question.objects.none()


def sync_neo4j_to_postgresql(request):
    """
    Fetches data from Neo4j (Subjects, Chapters, Topics) and
    stores it into the PostgreSQL 'topics' table.
    """
    if request.method != 'GET':
        return JsonResponse({"error": "This endpoint only supports GET requests."}, status=405)

    # Your provided Cypher query
    cypher_query = """
    MATCH (s:Subject)-[:CONTAINS]->(c:Chapter)-[:CONTAINS]->(t:Topic)
    RETURN DISTINCT s.name AS Subject, c.name AS Chapter, t.name AS Topic
    ORDER BY Subject, Chapter, Topic
    """
    
    topics_synced_count = 0
    topics_skipped_count = 0 # Will count skipped duplicates if unique_together is set
    topics_failed_count = 0
    errors = []

    # Define a default icon value since your Neo4j query doesn't return one,
    # and your PostgreSQL 'icon' field is not nullable.
    DEFAULT_ICON = "📚" # You can change this to a more meaningful default like "default_icon.png" or ""

    try:
        # Execute the Cypher query
        results, columns = db.cypher_query(cypher_query)
        
        # Verify the columns returned by the query
        expected_columns = ['Subject', 'Chapter', 'Topic']
        if not all(col in columns for col in expected_columns):
            raise ValueError(
                f"Neo4j query did not return all expected columns. "
                f"Expected: {expected_columns}, Got: {columns}"
            )

        subject_idx = columns.index('Subject')
        chapter_idx = columns.index('Chapter')
        topic_idx = columns.index('Topic')

        # Use a Django database transaction for atomicity when saving to PostgreSQL
        with transaction.atomic():
            for row in results:
                subject_name = row[subject_idx]
                chapter_name = row[chapter_idx]
                topic_name = row[topic_idx]

                try:
                    Topic.objects.create(
                        name=topic_name,
                        subject=subject_name,
                        icon=DEFAULT_ICON,
                        chapter=chapter_name if chapter_name is not None else ""
                    )
                    topics_synced_count += 1

                except IntegrityError as e:
                    # This block will ONLY be triggered if you have `unique_together`
                    # set on your Topic model and a duplicate is attempted.
                    logger.info(f"Skipping duplicate due to IntegrityError: Subject='{subject_name}', Chapter='{chapter_name}', Topic='{topic_name}' - Error: {e}")
                    topics_skipped_count += 1
                except Exception as e:
                    error_msg = f"Error saving topic '{topic_name}' (Subject: '{subject_name}', Chapter: '{chapter_name}') to PostgreSQL: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    topics_failed_count += 1

    except Exception as e:
        error_msg = f"Overall error fetching data from Neo4j or during transaction: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return JsonResponse({"status": "failed", "message": "An error occurred during synchronization.", "details": errors}, status=500)

    response_data = {
        "status": "success",
        "message": "Neo4j data synchronization to PostgreSQL completed.",
        "topics_synced": topics_synced_count,
        "topics_skipped_duplicates": topics_skipped_count, # Only effective if unique_together is set
        "topics_failed_to_save": topics_failed_count,
        "errors": errors
    }
    return JsonResponse(response_data)


def reset_chapter_structure():
    """
    Resets the chapter structure in Neo4j by clearing all existing nodes and relationships.
    Replicates the functionality from the original views.py reset utility.
    """
    try:
        # Clear all nodes and relationships
        db.cypher_query("MATCH (n) DETACH DELETE n")
        
        return {
            'status': 'success',
            'message': 'Chapter structure reset successfully. All Neo4j nodes and relationships have been cleared.'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error resetting chapter structure: {str(e)}'
        }


def sync_questions_from_neo4j(request=None):
    """
    Syncs questions from Neo4j to PostgreSQL Question model.
    Fetches questions with their options, correct answers, and topics.
    
    IMPORTANT: This function assumes topics are already populated by sync_neo4j_to_postgresql.
    It will NOT create new topics, only reference existing ones.
    """
    try:
        # Cypher query to fetch questions from Neo4j
        cypher_query = """
        MATCH (q:Question)
        RETURN 
          q.question_text AS question_text,
          q.options AS options,
          q.correct_option AS correct_option,
          q.topic_name AS topic_name
        """
        
        # Execute the query
        results, meta = db.cypher_query(cypher_query)
        
        if not results:
            response_data = {
                'status': 'success',
                'message': 'No questions found in Neo4j database.',
                'questions_processed': 0
            }
            if request:
                return JsonResponse(response_data)
            return response_data
        
        questions_created = 0
        errors = []
        topics_not_found = set()  # Track missing topics
        
        for row in results:
            try:
                question_text = row[0]
                options = row[1]  # This should be a list of 4 options
                correct_option = row[2]  # This should be the correct answer
                topic_name = row[3]
                
                # Validate required fields
                if not question_text or not question_text.strip():
                    errors.append(f"Skipping question with empty text")
                    continue
                
                if not topic_name or not topic_name.strip():
                    errors.append(f"Skipping question '{question_text[:50]}...' - no topic name")
                    continue
                
                # Handle options list validation
                if not options or not isinstance(options, list) or len(options) != 4:
                    errors.append(f"Skipping question '{question_text[:50]}...' - invalid options format (expected list of 4)")
                    continue
                
                # Validate all options are non-empty
                if not all(option and option.strip() for option in options):
                    errors.append(f"Skipping question '{question_text[:50]}...' - one or more options are empty")
                    continue
                
                # Extract and normalize correct_option
                if correct_option and isinstance(correct_option, str):
                    # Handle format like "(c) some text" or "(c)"
                    if correct_option.startswith('(') and ')' in correct_option:
                        correct_letter = correct_option[1:correct_option.index(')')].strip().lower()
                    else:
                        correct_letter = correct_option.strip().lower()
                    
                    # Normalize to uppercase A, B, C, D
                    if correct_letter in ['a', '0']:
                        correct_answer = 'A'
                    elif correct_letter in ['b', '1']:
                        correct_answer = 'B'
                    elif correct_letter in ['c', '2']:
                        correct_answer = 'C'
                    elif correct_letter in ['d', '3']:
                        correct_answer = 'D'
                    else:
                        errors.append(f"Skipping question '{question_text[:50]}...' - invalid correct_option: {correct_option}")
                        continue
                else:
                    errors.append(f"Skipping question '{question_text[:50]}...' - missing correct_option")
                    continue
                
                # ✅ FIXED: Only look for existing topics, don't create new ones
                topic = Topic.objects.filter(name=topic_name.strip()).first()
                
                if not topic:
                    # Track missing topics but don't create them
                    topics_not_found.add(topic_name.strip())
                    errors.append(f"Skipping question '{question_text[:50]}...' - topic '{topic_name}' not found in database. Run sync_neo4j_to_postgresql first.")
                    continue
                
                # Clean and prepare question data with regex handling
                question_text_clean = clean_mathematical_text(question_text.strip())
                
                # Clean all options
                cleaned_options = [clean_mathematical_text(option.strip()) for option in options]
                
                question_data = {
                    'topic': topic,
                    'question': question_text_clean,
                    'option_a': cleaned_options[0],
                    'option_b': cleaned_options[1],
                    'option_c': cleaned_options[2],
                    'option_d': cleaned_options[3],
                    'correct_answer': correct_answer,
                    'explanation': 'Explanation not available'  # Default explanation
                }
                
                # Create new question (no duplicate checking as per requirement)
                Question.objects.create(**question_data)
                questions_created += 1
                    
            except Exception as e:
                error_msg = f"Error processing question: {str(e)}"
                errors.append(error_msg)
                continue
        
        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Successfully created {questions_created} questions from Neo4j',
            'questions_created': questions_created,
            'total_processed': questions_created,
            'errors_count': len(errors)
        }
        
        if topics_not_found:
            response_data['missing_topics'] = list(topics_not_found)
            response_data['missing_topics_count'] = len(topics_not_found)
            response_data['recommendation'] = 'Run sync_neo4j_to_postgresql first to populate topics'
        
        if errors:
            response_data['errors'] = errors[:10]  # Limit errors to first 10
            if len(errors) > 10:
                response_data['additional_errors'] = f"... and {len(errors) - 10} more errors"
        
        if request:
            return JsonResponse(response_data)
        return response_data
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Failed to sync questions from Neo4j: {str(e)}',
            'questions_processed': 0
        }
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response


def clean_existing_questions(request=None):
    """
    API endpoint to clean mathematical expressions in existing questions.
    Can be called via API or as a utility function.
    """
    try:
        # Find questions that likely contain LaTeX/regex patterns
        questions_to_clean = Question.objects.filter(
            question__iregex=r'\\\\|\\$|\\^\\{|_\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta'
        )
        
        total_questions = questions_to_clean.count()
        
        if total_questions == 0:
            response_data = {
                'status': 'success',
                'message': 'No questions found that need cleaning',
                'questions_processed': 0,
                'questions_cleaned': 0
            }
            if request:
                return JsonResponse(response_data)
            return response_data
        
        processed = 0
        cleaned = 0
        batch_size = 100
        
        with transaction.atomic():
            for i in range(0, total_questions, batch_size):
                batch = questions_to_clean[i:i + batch_size]
                
                for question in batch:
                    original_question = question.question
                    original_options = [
                        question.option_a, question.option_b, 
                        question.option_c, question.option_d
                    ]
                    
                    # Clean the text
                    cleaned_question = clean_mathematical_text(question.question)
                    cleaned_options = [
                        clean_mathematical_text(question.option_a),
                        clean_mathematical_text(question.option_b),
                        clean_mathematical_text(question.option_c),
                        clean_mathematical_text(question.option_d)
                    ]
                    
                    # Check if any changes were made
                    changes_made = (
                        original_question != cleaned_question or
                        original_options != cleaned_options
                    )
                    
                    if changes_made:
                        question.question = cleaned_question
                        question.option_a = cleaned_options[0]
                        question.option_b = cleaned_options[1]
                        question.option_c = cleaned_options[2]
                        question.option_d = cleaned_options[3]
                        question.save(update_fields=[
                            'question', 'option_a', 'option_b', 'option_c', 'option_d'
                        ])
                        cleaned += 1
                    
                    processed += 1
        
        response_data = {
            'status': 'success',
            'message': f'Successfully cleaned {cleaned} questions out of {processed} processed',
            'questions_processed': processed,
            'questions_cleaned': cleaned
        }
        
        if request:
            return JsonResponse(response_data)
        return response_data
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Failed to clean existing questions: {str(e)}',
            'questions_processed': 0,
            'questions_cleaned': 0
        }
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response

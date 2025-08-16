from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models import Topic, Question, TestSession, TestAnswer, StudentProfile, DatabaseQuestion
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
        # Define character maps early for use throughout the function
        superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
        subscript_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'}
        
        # Handle simple chemical notations (before LaTeX processing)
        # Convert simple ion notations: 2NO2^ - -> 2NO₂⁻, 2H^ + -> 2H⁺
        text = re.sub(r'(\w+)\^ -', r'\1⁻', text)  # NO2^ - -> NO₂⁻
        text = re.sub(r'(\w+)\^ \+', r'\1⁺', text)  # H^ + -> H⁺
        text = re.sub(r'(\w+)\^-', r'\1⁻', text)   # NO2^- -> NO₂⁻
        text = re.sub(r'(\w+)\^\+', r'\1⁺', text)   # H^+ -> H⁺
        
        # Handle more complex ion patterns with multiple charges
        text = re.sub(r'(\w+)\^(\d+)-', lambda m: f"{m.group(1)}{superscript_map.get(m.group(2), m.group(2))}⁻", text)  # SO4^2- -> SO₄²⁻
        text = re.sub(r'(\w+)\^(\d+)\+', lambda m: f"{m.group(1)}{superscript_map.get(m.group(2), m.group(2))}⁺", text)  # Ca^2+ -> Ca²⁺
        
        # Convert scientific notation: 4 x 10^13 -> 4 × 10¹³
        text = re.sub(r'(\d+\.?\d*) x 10\^(\d+)', 
                     lambda m: f"{m.group(1)} × 10{''.join(superscript_map.get(d, d) for d in m.group(2))}", 
                     text)
        
        # Also handle scientific notation with * instead of x
        text = re.sub(r'(\d+\.?\d*) \* 10\^(\d+)', 
                     lambda m: f"{m.group(1)} × 10{''.join(superscript_map.get(d, d) for d in m.group(2))}", 
                     text)
        
        # Handle subscripts in chemical formulas: H2O -> H₂O, CO2 -> CO₂
        text = re.sub(r'([A-Za-z])(\d)', lambda m: f"{m.group(1)}{subscript_map.get(m.group(2), m.group(2))}", text)
        
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
        text = re.sub(r'\^\{([0-9]+)\}', lambda m: ''.join(superscript_map.get(d, d) for d in m.group(1)), text)
        text = re.sub(r'\^([0-9])', lambda m: superscript_map.get(m.group(1), m.group(1)), text)
        
        # Handle subscripts: _{2} or _2 -> ₂
        text = re.sub(r'_\{([0-9]+)\}', lambda m: ''.join(subscript_map.get(d, d) for d in m.group(1)), text)
        text = re.sub(r'_([0-9])', lambda m: subscript_map.get(m.group(1), m.group(1)), text)
        
        # Convert common LaTeX symbols to Unicode (enhanced with more symbols)
        symbol_replacements = {
            # Greek letters (lowercase)
            r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ', r'\\delta': 'δ',
            r'\\epsilon': 'ε', r'\\zeta': 'ζ', r'\\eta': 'η', r'\\theta': 'θ',
            r'\\iota': 'ι', r'\\kappa': 'κ', r'\\lambda': 'λ', r'\\mu': 'μ',
            r'\\nu': 'ν', r'\\xi': 'ξ', r'\\pi': 'π', r'\\rho': 'ρ',
            r'\\sigma': 'σ', r'\\tau': 'τ', r'\\upsilon': 'υ', r'\\phi': 'φ',
            r'\\chi': 'χ', r'\\psi': 'ψ', r'\\omega': 'ω',
            # Greek letters (uppercase)
            r'\\Alpha': 'Α', r'\\Beta': 'Β', r'\\Gamma': 'Γ', r'\\Delta': 'Δ',
            r'\\Epsilon': 'Ε', r'\\Zeta': 'Ζ', r'\\Eta': 'Η', r'\\Theta': 'Θ',
            r'\\Iota': 'Ι', r'\\Kappa': 'Κ', r'\\Lambda': 'Λ', r'\\Mu': 'Μ',
            r'\\Nu': 'Ν', r'\\Xi': 'Ξ', r'\\Pi': 'Π', r'\\Rho': 'Ρ',
            r'\\Sigma': 'Σ', r'\\Tau': 'Τ', r'\\Upsilon': 'Υ', r'\\Phi': 'Φ',
            r'\\Chi': 'Χ', r'\\Psi': 'Ψ', r'\\Omega': 'Ω',
            # Mathematical operators
            r'\\times': '×', r'\\div': '÷', r'\\pm': '±', r'\\mp': '∓',
            r'\\leq': '≤', r'\\geq': '≥', r'\\neq': '≠', r'\\approx': '≈',
            r'\\equiv': '≡', r'\\propto': '∝', r'\\sim': '∼', r'\\simeq': '≃',
            r'\\ll': '≪', r'\\gg': '≫', r'\\subset': '⊂', r'\\supset': '⊃',
            r'\\in': '∈', r'\\notin': '∉', r'\\cup': '∪', r'\\cap': '∩',
            # Mathematical symbols
            r'\\infty': '∞', r'\\sum': '∑', r'\\prod': '∏', r'\\int': '∫',
            r'\\oint': '∮', r'\\iint': '∬', r'\\iiint': '∭',
            r'\\partial': '∂', r'\\nabla': '∇', r'\\degree': '°',
            r'\\cdot': '·', r'\\bullet': '•', r'\\circ': '∘',
            r'\\rightarrow': '→', r'\\leftarrow': '←', r'\\leftrightarrow': '↔',
            r'\\Rightarrow': '⇒', r'\\Leftarrow': '⇐', r'\\Leftrightarrow': '⇔',
            # Fractions and roots (additional patterns)
            r'\\half': '½', r'\\third': '⅓', r'\\quarter': '¼',
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
        
        # Handle chemical formulas with parentheses like Ca(OH)2 -> Ca(OH)₂
        text = re.sub(r'\)(\d)', lambda m: f"){subscript_map.get(m.group(1), m.group(1))}", text)
        
        # Handle molecular formulas with brackets like [Cu(NH3)4]2+ -> [Cu(NH₃)₄]²⁺
        text = re.sub(r'\](\d+)', lambda m: f"]{subscript_map.get(m.group(1), m.group(1))}", text)
        
        # Clean up multiple spaces and whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove any remaining backslashes that aren't part of valid escape sequences
        text = re.sub(r'\\(?![nrtbf\'\"\\])', '', text)
        
        # Final cleanup: remove any stray braces that might be left
        text = re.sub(r'\{+', '', text)
        text = re.sub(r'\}+', '', text)
        
        return text
        
    except Exception as e:
        logger.warning(f"Error cleaning mathematical text: {e}. Original: {original_text[:100]}...")
        # Return original text if cleaning fails
        return original_text


def generate_questions_for_topics(selected_topics, question_count=None):
    """
    Generate questions for the selected topics with cleaned mathematical expressions.
    Enhanced with fallback logic for topics without questions.
    
    Args:
        selected_topics: List of topic IDs
        question_count: Maximum number of questions to return (optional)
    
    Returns:
        QuerySet of Question objects with cleaned text
    """
    try:
        # Get all questions for the selected topics
        questions = Question.objects.filter(topic_id__in=selected_topics)
        
        logger.info(f"Found {questions.count()} questions for topics {selected_topics}")
        
        # If no questions found for selected topics, try to find any available questions
        if questions.count() == 0:
            logger.warning(f"No questions found for selected topics {selected_topics}")
            
            # Fallback: Get questions from any topics that have questions
            available_topic_ids = Question.objects.values_list('topic_id', flat=True).distinct()
            if available_topic_ids.exists():
                # Randomly select from available topics
                import random
                fallback_topics = list(available_topic_ids)[:20]  # Limit to first 20 for performance
                random.shuffle(fallback_topics)
                questions = Question.objects.filter(topic_id__in=fallback_topics)
                logger.info(f"Fallback: Using {questions.count()} questions from available topics {fallback_topics[:10]}")
            else:
                logger.error("No questions found in the entire database!")
                return Question.objects.none()
        
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
            # Check if question text contains LaTeX patterns OR simple chemical notations (enhanced pattern detection)
            patterns_to_check = ['\\', '$', '^{', '_{', '\\frac', '\\sqrt', '\\alpha', '\\beta', '^ -', '^ +', '^-', '^+', 'x 10^', '\\mathrm', '\\text']
            needs_cleaning = any(pattern in question.question for pattern in patterns_to_check)
            if not needs_cleaning:
                # Also check options for patterns
                all_options = question.option_a + question.option_b + question.option_c + question.option_d
                needs_cleaning = any(pattern in all_options for pattern in patterns_to_check)
            if not needs_cleaning and question.explanation:
                # Also check explanation for patterns
                needs_cleaning = any(pattern in question.explanation for pattern in patterns_to_check)
            
            if needs_cleaning:
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                if question.explanation:
                    question.explanation = clean_mathematical_text(question.explanation)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'])
        
        logger.info(f"Generated {questions.count()} questions for topics {selected_topics}")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions for topics {selected_topics}: {str(e)}")
        # Return empty queryset if there's an error
        return Question.objects.none()


@api_view(['GET'])
def sync_topics_from_database_question(request=None):
    """
    Syncs unique topics from the database_question table to the Topic model.
    Only creates new topics that don't already exist based on (name, subject, chapter) combination.
    """
    try:
        # Get unique combinations of subject, chapter, topic from database_question table
        unique_topics = (
            DatabaseQuestion.objects
            .values('subject', 'chapter', 'topic')
            .distinct()
            .filter(
                subject__isnull=False,
                topic__isnull=False
            )
            .exclude(subject__exact='')
            .exclude(topic__exact='')
        )

        topics_synced_count = 0
        topics_skipped_count = 0
        topics_failed_count = 0
        errors = []
        DEFAULT_ICON = "📚"

        with transaction.atomic():
            for entry in unique_topics:
                subject_name = entry['subject'] or ""
                chapter_name = entry['chapter'] or ""
                topic_name = entry['topic'] or ""

                if not topic_name.strip():
                    errors.append(f"Skipping topic with empty name (Subject: '{subject_name}', Chapter: '{chapter_name}')")
                    continue

                try:
                    # Check if topic already exists with same name, subject, and chapter
                    existing_topic = Topic.objects.filter(
                        name=topic_name.strip(),
                        subject=subject_name.strip(),
                        chapter=chapter_name.strip()
                    ).first()
                    
                    if existing_topic:
                        topics_skipped_count += 1
                        continue
                    
                    # Create new topic only if it doesn't exist
                    Topic.objects.create(
                        name=topic_name.strip(),
                        subject=subject_name.strip(),
                        icon=DEFAULT_ICON,
                        chapter=chapter_name.strip()
                    )
                    topics_synced_count += 1
                    
                except IntegrityError as e:
                    errors.append(f"IntegrityError creating topic '{topic_name}': {e}")
                    topics_skipped_count += 1
                except Exception as e:
                    errors.append(f"Error saving topic '{topic_name}': {e}")
                    topics_failed_count += 1

        response_data = {
            "status": "success",
            "message": "PostgreSQL topic sync completed.",
            "topics_synced": topics_synced_count,
            "topics_skipped_duplicates": topics_skipped_count,
            "topics_failed_to_save": topics_failed_count,
            "total_unique_topics_found": unique_topics.count(),
            "errors": errors
        }
        
        if request:
            return JsonResponse(response_data)
        return response_data

    except Exception as e:
        error_msg = f"Error syncing topics from database_question: {e}"
        logger.error(error_msg)
        error_response = {"status": "failed", "message": error_msg}
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response


@api_view(['DELETE'])
def reset_questions_and_topics(request=None):
    """
    Resets the Question and Topic tables by clearing all existing data.
    This allows for a fresh sync from database_question table.
    """
    try:
        with transaction.atomic():
            # Delete all questions first (due to foreign key constraints)
            questions_deleted = Question.objects.all().delete()[0]
            # Delete all topics
            topics_deleted = Topic.objects.all().delete()[0]
        
        response_data = {
            'status': 'success',
            'message': f'Reset completed successfully. Deleted {questions_deleted} questions and {topics_deleted} topics.',
            'questions_deleted': questions_deleted,
            'topics_deleted': topics_deleted
        }
        
        if request:
            return JsonResponse(response_data)
        return response_data
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Error resetting questions and topics: {str(e)}'
        }
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response


@api_view(['GET'])
def sync_questions_from_database_question(request=None):
    """
    Syncs questions from database_question table to PostgreSQL Question model.
    Fetches questions with their options, correct answers, and topics.
    
    IMPORTANT: This function assumes topics are already populated by sync_topics_from_database_question.
    It will NOT create new topics, only reference existing ones.
    Only creates new questions that don't already exist based on question content and topic.
    """
    try:
        # Get all questions from database_question table
        source_questions = DatabaseQuestion.objects.filter(
            question_text__isnull=False,
            topic__isnull=False,
            option_1__isnull=False,
            option_2__isnull=False,
            option_3__isnull=False,
            option_4__isnull=False,
            correct_answer__isnull=False
        ).exclude(
            question_text__exact=''
        ).exclude(
            topic__exact=''
        )

        if not source_questions.exists():
            response_data = {
                'status': 'success',
                'message': 'No valid questions found in database_question table.',
                'questions_processed': 0
            }
            if request:
                return JsonResponse(response_data)
            return response_data

        questions_created = 0
        questions_skipped = 0
        errors = []
        topics_not_found = set()  # Track missing topics

        with transaction.atomic():
            for q in source_questions:
                try:
                    question_text = q.question_text
                    options = [q.option_1, q.option_2, q.option_3, q.option_4]
                    correct_option = q.correct_answer
                    topic_name = q.topic

                    # Validate required fields
                    if not question_text or not question_text.strip():
                        errors.append("Skipping question with empty text")
                        continue

                    if not topic_name or not topic_name.strip():
                        errors.append(f"Skipping question '{question_text[:50]}...' - no topic name")
                        continue

                    # Validate all options are non-empty
                    if not all(options) or not all(opt and opt.strip() for opt in options):
                        errors.append(f"Skipping question '{question_text[:50]}...' - invalid options")
                        continue

                    if not correct_option or not correct_option.strip():
                        errors.append(f"Skipping question '{question_text[:50]}...' - missing correct_option")
                        continue

                    # Normalize correct_option to A, B, C, D
                    correct_letter = correct_option.strip().lower()
                    
                    # Handle various formats like "(a)", "a", "1", etc.
                    if correct_letter.startswith('(') and ')' in correct_letter:
                        correct_letter = correct_letter[1:correct_letter.index(')')].strip().lower()
                    
                    if correct_letter in ['a', '1', 'option_1']:
                        correct_answer = 'A'
                    elif correct_letter in ['b', '2', 'option_2']:
                        correct_answer = 'B'
                    elif correct_letter in ['c', '3', 'option_3']:
                        correct_answer = 'C'
                    elif correct_letter in ['d', '4', 'option_4']:
                        correct_answer = 'D'
                    else:
                        errors.append(f"Skipping question '{question_text[:50]}...' - invalid correct_option: {correct_option}")
                        continue

                    # Look for existing topic
                    topic = Topic.objects.filter(name=topic_name.strip()).first()
                    if not topic:
                        topics_not_found.add(topic_name.strip())
                        errors.append(f"Skipping question '{question_text[:50]}...' - topic '{topic_name}' not found.")
                        continue

                    # Clean question text and options
                    question_text_clean = clean_mathematical_text(question_text.strip())
                    cleaned_options = [clean_mathematical_text(opt.strip()) for opt in options]
                    cleaned_explanation = clean_mathematical_text(q.explanation) if q.explanation else 'Explanation not available'

                    # Check if question already exists (avoid duplicates)
                    existing_question = Question.objects.filter(
                        question=question_text_clean,
                        topic=topic,
                        option_a=cleaned_options[0],
                        option_b=cleaned_options[1],
                        option_c=cleaned_options[2],
                        option_d=cleaned_options[3]
                    ).first()
                    
                    if existing_question:
                        questions_skipped += 1
                        continue

                    # Prepare question data
                    question_data = {
                        'topic': topic,
                        'question': question_text_clean,
                        'option_a': cleaned_options[0],
                        'option_b': cleaned_options[1],
                        'option_c': cleaned_options[2],
                        'option_d': cleaned_options[3],
                        'correct_answer': correct_answer,
                        'explanation': cleaned_explanation
                    }

                    # Create new question
                    Question.objects.create(**question_data)
                    questions_created += 1

                except Exception as e:
                    error_msg = f"Error processing question: {str(e)}"
                    errors.append(error_msg)
                    continue

        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Successfully created {questions_created} questions from database_question table',
            'questions_created': questions_created,
            'questions_skipped': questions_skipped,
            'total_processed': questions_created + questions_skipped,
            'errors_count': len(errors)
        }

        if topics_not_found:
            response_data['missing_topics'] = list(topics_not_found)
            response_data['missing_topics_count'] = len(topics_not_found)
            response_data['recommendation'] = 'Run sync_topics_from_database_question first to populate topics'

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
            'message': f'Failed to sync questions from database_question: {str(e)}',
            'questions_processed': 0
        }

        if request:
            return JsonResponse(error_response, status=500)
        return error_response


@api_view(['GET'])
def sync_all_from_database_question(request=None):
    """
    Performs complete sync from database_question table to Topic and Question models.
    First syncs topics, then syncs questions.
    """
    try:
        # Step 1: Sync topics
        topics_result = sync_topics_from_database_question()
        
        # Step 2: Sync questions
        questions_result = sync_questions_from_database_question()
        
        # Combine results
        combined_result = {
            'status': 'success',
            'message': 'Complete sync from database_question table completed',
            'topics_sync': topics_result,
            'questions_sync': questions_result,
            'summary': {
                'topics_created': topics_result.get('topics_synced', 0),
                'topics_skipped': topics_result.get('topics_skipped_duplicates', 0),
                'questions_created': questions_result.get('questions_created', 0),
                'questions_skipped': questions_result.get('questions_skipped', 0),
                'total_errors': (
                    topics_result.get('errors_count', 0) + 
                    questions_result.get('errors_count', 0)
                )
            }
        }
        
        if request:
            return JsonResponse(combined_result)
        return combined_result
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Failed to complete sync from database_question: {str(e)}'
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
        # Find questions that likely contain LaTeX/regex patterns OR simple chemical notations
        # Check in question text, options, and explanation
        from django.db.models import Q
        questions_to_clean = Question.objects.filter(
            Q(question__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_a__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_b__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_c__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_d__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(explanation__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^')
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
                    original_explanation = question.explanation
                    
                    # Clean the text
                    cleaned_question = clean_mathematical_text(question.question)
                    cleaned_options = [
                        clean_mathematical_text(question.option_a),
                        clean_mathematical_text(question.option_b),
                        clean_mathematical_text(question.option_c),
                        clean_mathematical_text(question.option_d)
                    ]
                    cleaned_explanation = clean_mathematical_text(question.explanation) if question.explanation else question.explanation
                    
                    # Check if any changes were made
                    changes_made = (
                        original_question != cleaned_question or
                        original_options != cleaned_options or
                        original_explanation != cleaned_explanation
                    )
                    
                    if changes_made:
                        question.question = cleaned_question
                        question.option_a = cleaned_options[0]
                        question.option_b = cleaned_options[1]
                        question.option_c = cleaned_options[2]
                        question.option_d = cleaned_options[3]
                        question.explanation = cleaned_explanation
                        question.save(update_fields=[
                            'question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'
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

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models import Topic, Question, TestSession, TestAnswer, StudentProfile
from external_db.models import DatabaseQuestion
import logging
from django.db import transaction, IntegrityError
import random
import re

logger = logging.getLogger(__name__)


def normalize_subject(subject_raw: str) -> str:
    """
    Normalize various subject name variants to canonical subject names used in Topic model.

    Returns one of: 'Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math'
    or None if the subject cannot be normalized.
    """
    if not subject_raw:
        return None
    s = str(subject_raw).strip().lower()
    if not s:
        return None

    mapping = {
        'physics': 'Physics', 'phys': 'Physics', 'phy': 'Physics',
        'chemistry': 'Chemistry', 'chem': 'Chemistry',
        'botany': 'Botany', 'plant biology': 'Botany',
        'zoology': 'Zoology', 'animal biology': 'Zoology', 'zoo': 'Zoology',
        'biology': 'Biology', 'bio': 'Biology',
        'math': 'Math', 'mathematics': 'Math', 'maths': 'Math'
    }

    # Normalize common punctuation and multiple spaces
    s = re.sub(r'[\s\-_]+', ' ', s).strip()

    # Direct mapping
    if s in mapping:
        return mapping[s]

    # Try to match prefixes (e.g., 'physics - mechanics')
    for key in mapping.keys():
        if s.startswith(key):
            return mapping[key]

    # Try to match if the word appears anywhere
    for key in mapping.keys():
        if key in s:
            return mapping[key]

    # As a last resort, capitalize and accept if it matches allowed set
    candidate = s.capitalize()
    if candidate in ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']:
        return candidate

    return None


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


def generate_questions_for_topics(selected_topics, question_count=None, exclude_question_ids=None, difficulty_distribution=None):
    """
    Generate questions for the selected topics with cleaned mathematical expressions.
    Enhanced with fallback logic for topics without questions and question exclusion.
    
    Args:
        selected_topics: List of topic IDs
        question_count: Maximum number of questions to return (optional)
        exclude_question_ids: Set/list of question IDs to exclude (for preventing repetition)
        difficulty_distribution: Override default difficulty distribution
    
    Returns:
        QuerySet of Question objects with cleaned text
    """
    from ..services.selection_engine import generate_questions_with_rules
    from django.conf import settings
    import random
    
    # Try new rule-based engine first
    try:
        neet_settings = getattr(settings, 'NEET_SETTINGS', {})
        if neet_settings.get('USE_RULE_ENGINE', True) and question_count:
            logger.info("Using rule-based selection engine")
            
            # Convert exclude_question_ids to set
            exclude_ids = set(exclude_question_ids) if exclude_question_ids else set()
            
            # Call rule engine
            rule_engine_result = generate_questions_with_rules(
                selected_topics=selected_topics,
                question_count=question_count,
                test_type="topic",
                exclude_question_ids=exclude_ids,
                difficulty_distribution=difficulty_distribution
            )
            
            if rule_engine_result is not None and rule_engine_result.exists():
                logger.info(f"Rule engine selected {rule_engine_result.count()} questions")
                return rule_engine_result
            else:
                logger.warning("Rule engine returned no questions, falling back to legacy method")
        
    except Exception as e:
        logger.exception(f"Rule engine failed: {e}, falling back to legacy method")
    
    # Legacy selection logic (fallback)
    logger.info("Using legacy selection method")
    
    try:
        # Initialize exclude_question_ids as empty set if not provided
        if exclude_question_ids is None:
            exclude_question_ids = set()
        else:
            # Ensure it's a set for efficient lookup
            exclude_question_ids = set(exclude_question_ids)

        # Get all questions for the selected topics, excluding recent ones
        questions = Question.objects.filter(topic_id__in=selected_topics)
        if exclude_question_ids:
            questions = questions.exclude(id__in=exclude_question_ids)
        
        logger.info(f"Found {questions.count()} questions for topics {selected_topics} (excluded {len(exclude_question_ids)} recent questions)")
        
        # If no questions found for selected topics after exclusion, try fallback strategies
        if questions.count() == 0:
            logger.warning(f"No questions found for selected topics {selected_topics} after excluding recent questions")
            
            # Strategy 1: Try all questions from selected topics (ignoring exclusions temporarily)
            all_questions_for_topics = Question.objects.filter(topic_id__in=selected_topics)
            if all_questions_for_topics.exists():
                questions = all_questions_for_topics
                logger.info(f"Fallback 1: Using all {questions.count()} questions from selected topics (ignoring exclusions)")
            else:
                # Strategy 2: Get questions from any topics that have questions
                available_topic_ids = Question.objects.values_list('topic_id', flat=True).distinct()
                if available_topic_ids.exists():
                    # Randomly select from available topics, excluding recent questions
                    fallback_topics = list(available_topic_ids)[:20]  # Limit to first 20 for performance
                    random.shuffle(fallback_topics)
                    questions = Question.objects.filter(topic_id__in=fallback_topics)
                    if exclude_question_ids:
                        questions = questions.exclude(id__in=exclude_question_ids)
                    
                    # If still no questions after excluding recent ones, use all available
                    if questions.count() == 0:
                        questions = Question.objects.filter(topic_id__in=fallback_topics)
                        logger.info(f"Fallback 2b: Using all {questions.count()} questions from available topics (ignoring exclusions)")
                    else:
                        logger.info(f"Fallback 2a: Using {questions.count()} questions from available topics {fallback_topics[:10]} (excluded recent)")
                else:
                    logger.error("No questions found in the entire database!")
                    return Question.objects.none()
        
        # If difficulty distribution is requested, try to select per-difficulty
        if difficulty_distribution and question_count:
            # difficulty_distribution can be percentages (sum 100) or absolute counts
            dist = difficulty_distribution.copy() if isinstance(difficulty_distribution, dict) else {}
            easy_req = dist.get('easy')
            medium_req = dist.get('medium')
            hard_req = dist.get('hard')

            # If values look like percentages (sum 100), convert to counts
            if all(isinstance(x, (int, float)) for x in [easy_req or 0, medium_req or 0, hard_req or 0]):
                total_dist = (easy_req or 0) + (medium_req or 0) + (hard_req or 0)
                if total_dist == 100:
                    easy_req = int((easy_req or 0) * question_count / 100)
                    medium_req = int((medium_req or 0) * question_count / 100)
                    hard_req = int((hard_req or 0) * question_count / 100)

            # Fallback: if any are None, treat as 0
            easy_req = int(easy_req or 0)
            medium_req = int(medium_req or 0)
            hard_req = int(hard_req or 0)

            # Adjust rounding: ensure total equals question_count by adding to easy
            total_req = easy_req + medium_req + hard_req
            if total_req < question_count:
                easy_req += (question_count - total_req)

            # Normalize difficulty labels and partition questions in Python for robustness
            def _normalize_label(val):
                if not val:
                    return 'unknown'
                s = str(val).strip().lower()
                # common canonical variants
                if s in ('easy', 'e', '1', 'beginner', 'low'):
                    return 'easy'
                if s in ('medium', 'med', 'm', '2', 'intermediate'):
                    return 'medium'
                if s in ('hard', 'h', '3', 'advanced', 'high'):
                    return 'hard'
                # numeric strings like '1', '2', '3' handled above; try to map digits
                if s.isdigit():
                    if s == '1':
                        return 'easy'
                    if s == '2':
                        return 'medium'
                    if s == '3':
                        return 'hard'
                # fallback heuristics
                if 'easy' in s:
                    return 'easy'
                if 'medium' in s or 'intermediate' in s:
                    return 'medium'
                if 'hard' in s or 'advanced' in s:
                    return 'hard'
                return 'unknown'

            easy_list = []
            medium_list = []
            hard_list = []
            unknown_list = []

            # iterate once over questions to partition them deterministically
            for q in questions:
                label = _normalize_label(q.difficulty)
                if label == 'easy':
                    easy_list.append(q)
                elif label == 'medium':
                    medium_list.append(q)
                elif label == 'hard':
                    hard_list.append(q)
                else:
                    unknown_list.append(q)

            logger.info(f"Question difficulty buckets: easy={len(easy_list)}, medium={len(medium_list)}, hard={len(hard_list)}, unknown={len(unknown_list)}")

            selected = []
            used_ids = set()

            def take_from_list(lst, n, used_ids):
                if n <= 0 or not lst:
                    return []
                available = [q for q in lst if q.id not in used_ids]
                if not available:
                    return []
                random.shuffle(available)
                return available[:n]

            # Helper to try multiple buckets in order until we satisfy n
            def take_with_fallback(bucket_lists, n, used_ids):
                taken = []
                remaining = n
                for lst in bucket_lists:
                    if remaining <= 0:
                        break
                    if not lst:
                        continue
                    more = take_from_list(lst, remaining, used_ids)
                    if more:
                        taken.extend(more)
                        used_ids.update(q.id for q in more)
                        remaining = n - len(taken)
                return taken

            # Selection with ordered fallback per your requirement:
            # easy falls back to unknown
            # medium falls back to easy then unknown
            # hard falls back to medium then easy then unknown
            sel_easy = take_with_fallback([easy_list, unknown_list], easy_req, used_ids)
            selected.extend(sel_easy)

            sel_medium = take_with_fallback([medium_list, easy_list, unknown_list], medium_req, used_ids)
            selected.extend(sel_medium)

            sel_hard = take_with_fallback([hard_list, medium_list, easy_list, unknown_list], hard_req, used_ids)
            selected.extend(sel_hard)

            # If still shortages, fill from the remaining pool (any leftover question in the same topic set)
            if len(selected) < question_count:
                remaining_needed = question_count - len(selected)
                remaining_pool = [q for q in list(questions) if q.id not in used_ids]
                if remaining_pool:
                    random.shuffle(remaining_pool)
                    more = remaining_pool[:remaining_needed]
                    selected.extend(more); used_ids.update(q.id for q in more)

            logger.info(f"Selected per-difficulty counts -> easy={len(sel_easy)}, medium={len(sel_medium)}, hard={len(sel_hard)}, total_selected={len(selected)} (requested {question_count})")

            # Return queryset built from selected ids
            if selected:
                q_ids = [q.id for q in selected]
                return Question.objects.filter(id__in=q_ids)

            # else fall through to regular selection logic

        # If question_count is specified and we have more questions than needed,
        # prioritize non-excluded questions and randomly select
        if question_count and questions.count() > question_count:
            # Intelligent selection: prioritize newer questions (non-excluded) if available
            questions_list = list(questions)
            
            # If we have enough non-excluded questions, use only those
            non_excluded_questions = [q for q in questions_list if q.id not in exclude_question_ids]
            
            if len(non_excluded_questions) >= question_count:
                # Use only non-excluded questions
                random.shuffle(non_excluded_questions)
                selected_questions = non_excluded_questions[:question_count]
                logger.info(f"Selected {len(selected_questions)} questions (all non-excluded)")
            else:
                # Use all non-excluded questions + some excluded ones to reach the target
                random.shuffle(questions_list)
                selected_questions = questions_list[:question_count]
                excluded_count = sum(1 for q in selected_questions if q.id in exclude_question_ids)
                logger.info(f"Selected {len(selected_questions)} questions ({excluded_count} from recent tests due to insufficient pool)")
            
            # Return a queryset-like structure
            question_ids = [q.id for q in selected_questions]
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
            if not needs_cleaning and question.difficulty:
                # Also check difficulty for patterns
                needs_cleaning = any(pattern in question.difficulty for pattern in patterns_to_check)
            if not needs_cleaning and question.question_type:
                # Also check question_type for patterns
                needs_cleaning = any(pattern in question.question_type for pattern in patterns_to_check)
            
            if needs_cleaning:
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                if question.explanation:
                    question.explanation = clean_mathematical_text(question.explanation)
                if question.difficulty:
                    question.difficulty = clean_mathematical_text(question.difficulty)
                if question.question_type:
                    question.question_type = clean_mathematical_text(question.question_type)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation', 'difficulty', 'question_type'])
        
        excluded_in_final = sum(1 for q in questions if q.id in exclude_question_ids) if exclude_question_ids else 0
        logger.info(f"Generated {questions.count()} questions for topics {selected_topics} ({excluded_in_final} from recent tests)")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions for topics {selected_topics}: {str(e)}")
        # Return empty queryset if there's an error
        return Question.objects.none()


def generate_random_questions_from_database(question_count, exclude_question_ids=None):
    """
    Generate random questions directly from the entire database, bypassing topic selection.
    This is specifically for "Random Test" mode where we want a mix of questions from all subjects.
    
    Args:
        question_count: Number of questions to select
        exclude_question_ids: Set/list of question IDs to exclude (for preventing repetition)
    
    Returns:
        QuerySet of Question objects with cleaned text
    """
    from ..services.selection_engine import generate_questions_with_rules
    from django.conf import settings
    
    # Try new rule-based engine first
    try:
        neet_settings = getattr(settings, 'NEET_SETTINGS', {})
        if neet_settings.get('USE_RULE_ENGINE', True):
            logger.info("Using rule-based selection engine for random test")
            
            # Convert exclude_question_ids to set
            exclude_ids = set(exclude_question_ids) if exclude_question_ids else set()
            
            # Call rule engine with empty topics for random selection
            rule_engine_result = generate_questions_with_rules(
                selected_topics=[],  # Empty for random test
                question_count=question_count,
                test_type="random",
                exclude_question_ids=exclude_ids
            )
            
            if rule_engine_result is not None and rule_engine_result.exists():
                logger.info(f"Rule engine selected {rule_engine_result.count()} random questions")
                return rule_engine_result
            else:
                logger.warning("Rule engine returned no questions, falling back to legacy random method")
        
    except Exception as e:
        logger.exception(f"Rule engine failed for random test: {e}, falling back to legacy method")
    
    # Legacy random selection logic (fallback)
    logger.info("Using legacy random selection method")
    
    try:
        # Initialize exclude_question_ids as empty set if not provided
        if exclude_question_ids is None:
            exclude_question_ids = set()
        else:
            # Ensure it's a set for efficient lookup
            exclude_question_ids = set(exclude_question_ids)
        
        # Get all questions from the entire database, excluding recent ones
        all_questions = Question.objects.all()
        if exclude_question_ids:
            all_questions = all_questions.exclude(id__in=exclude_question_ids)
        
        total_available = all_questions.count()
        logger.info(f"Random test: Found {total_available} total questions available (excluded {len(exclude_question_ids)} recent questions)")
        
        # Check if we have enough questions
        if total_available < question_count:
            logger.warning(f"Random test: Requested {question_count} questions, but only {total_available} available after exclusions")
            # For random tests, use what we have rather than failing
            question_count = total_available
        
        # Randomly select questions ensuring good distribution across subjects
        subjects = ["Physics", "Chemistry", "Botany", "Zoology", "Biology", "Math"]
        questions_per_subject = max(1, question_count // len(subjects))  # At least 1 question per subject
        remaining_questions = question_count % len(subjects)  # Distribute remaining questions
        
        selected_questions = []
        
        for i, subject in enumerate(subjects):
            # Calculate questions for this subject
            subject_question_count = questions_per_subject
            if i < remaining_questions:  # Distribute remaining questions to first few subjects
                subject_question_count += 1
            
            # Get questions from this subject, excluding already selected ones and recent questions
            subject_questions = all_questions.filter(topic__subject=subject)
            if selected_questions:
                selected_ids = [q.id for q in selected_questions]
                subject_questions = subject_questions.exclude(id__in=selected_ids)
            
            # Randomly select questions from this subject
            if subject_questions.exists():
                subject_selected = list(subject_questions.order_by('?')[:subject_question_count])
                selected_questions.extend(subject_selected)
                logger.info(f"Random test: Selected {len(subject_selected)} questions from {subject}")
            else:
                logger.warning(f"Random test: No questions available for {subject}")
        
        # If we still need more questions (due to subject limitations), get from any remaining questions
        current_count = len(selected_questions)
        if current_count < question_count:
            selected_ids = [q.id for q in selected_questions]
            remaining_questions_needed = question_count - current_count
            
            additional_questions = all_questions.exclude(id__in=selected_ids).order_by('?')[:remaining_questions_needed]
            selected_questions.extend(list(additional_questions))
            logger.info(f"Random test: Added {len(additional_questions)} additional questions from any subject")
        
        # Convert to queryset
        if selected_questions:
            question_ids = [q.id for q in selected_questions]
            questions = Question.objects.filter(id__in=question_ids)
        else:
            questions = Question.objects.none()
        
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
            if not needs_cleaning and question.difficulty:
                # Also check difficulty for patterns
                needs_cleaning = any(pattern in question.difficulty for pattern in patterns_to_check)
            if not needs_cleaning and question.question_type:
                # Also check question_type for patterns
                needs_cleaning = any(pattern in question.question_type for pattern in patterns_to_check)
            
            if needs_cleaning:
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                if question.explanation:
                    question.explanation = clean_mathematical_text(question.explanation)
                if question.difficulty:
                    question.difficulty = clean_mathematical_text(question.difficulty)
                if question.question_type:
                    question.question_type = clean_mathematical_text(question.question_type)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation', 'difficulty', 'question_type'])
        
        logger.info(f"Random test: Successfully generated {questions.count()} random questions from entire database")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating random questions from database: {str(e)}")
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
            DatabaseQuestion.objects.using('source')
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
                    # Normalize subject before checks/creation
                    normalized_subject = normalize_subject(subject_name)
                    if not normalized_subject:
                        errors.append(f"Skipping topic '{topic_name.strip()}' due to unrecognized subject '{subject_name}'")
                        topics_failed_count += 1
                        continue

                    # Check if topic exists using normalized subject
                    existing_topic = Topic.objects.filter(
                        name=topic_name.strip(),
                        subject=normalized_subject,
                        chapter=chapter_name.strip()
                    ).first()
                    
                    if existing_topic:
                        topics_skipped_count += 1
                        continue
                    
                    # Create new topic only if it doesn't exist
                    Topic.objects.create(
                        name=topic_name.strip(),
                        subject=normalized_subject,
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
        # Get all questions from database_question table (from external 'source' DB)
        source_questions = DatabaseQuestion.objects.using('source').filter(
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
                    difficulty = q.difficulty
                    question_type = q.question_type

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

                    # Normalize correct_option: prefer mapping to A/B/C/D when the value
                    # clearly references an option; otherwise accept numeric or textual
                    # correct answers (useful for NVT). This keeps the sync permissive.
                    correct_answer = None
                    correct_letter = str(correct_option).strip()
                    # If value is like '(a)' or single-char, extract
                    if correct_letter.startswith('(') and ')' in correct_letter:
                        correct_letter = correct_letter[1:correct_letter.index(')')].strip()
                    low = correct_letter.lower()
                    if low in ['a', 'b', 'c', 'd']:
                        correct_answer = low.upper()
                    elif low in ['option_1', 'option 1', 'option a', '1', '1.0', 'first']:
                        correct_answer = 'A'
                    elif low in ['option_2', 'option 2', 'option b', '2', '2.0', 'second']:
                        correct_answer = 'B'
                    elif low in ['option_3', 'option 3', 'option c', '3', '3.0', 'third']:
                        correct_answer = 'C'
                    elif low in ['option_4', 'option 4', 'option d', '4', '4.0', 'fourth']:
                        correct_answer = 'D'
                    else:
                        # If it's numeric (integer or float), preserve as-is
                        import re
                        raw = str(correct_option).strip()
                        if re.match(r'^-?\d+(\.\d+)?$', raw):
                            correct_answer = raw
                        else:
                            # Otherwise accept trimmed text (useful for descriptive answers)
                            correct_answer = raw

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
                        # Update metadata fields for existing questions
                        updates = {}
                        new_difficulty = difficulty.strip() if difficulty else None
                        new_qtype = question_type.strip() if question_type else None
                        if new_difficulty and existing_question.difficulty != new_difficulty:
                            updates['difficulty'] = new_difficulty
                        if new_qtype and existing_question.question_type != new_qtype:
                            updates['question_type'] = new_qtype
                        # Optionally improve explanation if missing
                        if (not existing_question.explanation or existing_question.explanation == 'Explanation not available') and cleaned_explanation:
                            updates['explanation'] = cleaned_explanation
                        if updates:
                            for k, v in updates.items():
                                setattr(existing_question, k, v)
                            existing_question.save(update_fields=list(updates.keys()))
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
                        'explanation': cleaned_explanation,
                        'difficulty': difficulty.strip() if difficulty else None,
                        'question_type': question_type.strip() if question_type else None
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
        # Check in question text, options, explanation, difficulty, and question_type
        from django.db.models import Q
        questions_to_clean = Question.objects.filter(
            Q(question__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_a__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_b__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_c__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(option_d__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(explanation__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(difficulty__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^') |
            Q(question_type__iregex=r'\\\\|\\\$|\\\^\\\{|_\\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta|\^ -|\^ \+|\^-|\^\+|x 10\^')
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
                    original_difficulty = question.difficulty
                    original_question_type = question.question_type
                    
                    # Clean the text
                    cleaned_question = clean_mathematical_text(question.question)
                    cleaned_options = [
                        clean_mathematical_text(question.option_a),
                        clean_mathematical_text(question.option_b),
                        clean_mathematical_text(question.option_c),
                        clean_mathematical_text(question.option_d)
                    ]
                    cleaned_explanation = clean_mathematical_text(question.explanation) if question.explanation else question.explanation
                    cleaned_difficulty = clean_mathematical_text(question.difficulty) if question.difficulty else question.difficulty
                    cleaned_question_type = clean_mathematical_text(question.question_type) if question.question_type else question.question_type
                    
                    # Check if any changes were made
                    changes_made = (
                        original_question != cleaned_question or
                        original_options != cleaned_options or
                        original_explanation != cleaned_explanation or
                        original_difficulty != cleaned_difficulty or
                        original_question_type != cleaned_question_type
                    )
                    
                    if changes_made:
                        question.question = cleaned_question
                        question.option_a = cleaned_options[0]
                        question.option_b = cleaned_options[1]
                        question.option_c = cleaned_options[2]
                        question.option_d = cleaned_options[3]
                        question.explanation = cleaned_explanation
                        question.difficulty = cleaned_difficulty
                        question.question_type = cleaned_question_type
                        question.save(update_fields=[
                            'question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation', 'difficulty', 'question_type'
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


def adaptive_generate_questions_for_topics(selected_topics, question_count, student_id, exclude_question_ids=None):
    """
    Generate questions for topics using adaptive selection logic.
    
    Bucket A (New): 60% - Questions never attempted by the student
    Bucket B (Wrong/Unanswered): 30% - Questions answered incorrectly or left unanswered
    Bucket C (Correct): 10% - Questions answered correctly
    
    Args:
        selected_topics (list): List of topic IDs to select questions from
        question_count (int): Total number of questions to select
        student_id (str): Student ID to check answer history
        exclude_question_ids (set): Question IDs to exclude from selection
        
    Returns:
        QuerySet: Selected questions following adaptive logic
    """
    from django.conf import settings
    from django.db.models import Q
    
    if exclude_question_ids is None:
        exclude_question_ids = set()
    
    # Get adaptive ratios from settings
    neet_settings = getattr(settings, 'NEET_SETTINGS', {})
    ratio_new = neet_settings.get('ADAPTIVE_RATIO_NEW', 60) / 100
    ratio_wrong = neet_settings.get('ADAPTIVE_RATIO_WRONG', 30) / 100
    ratio_correct = neet_settings.get('ADAPTIVE_RATIO_CORRECT', 10) / 100
    
    logger.info(f"Adaptive selection for student {student_id}: {question_count} questions with ratios {ratio_new*100}%/{ratio_wrong*100}%/{ratio_correct*100}%")
    
    # Get all available questions for selected topics
    if selected_topics:
        all_questions = Question.objects.filter(topic_id__in=selected_topics)
    else:
        all_questions = Question.objects.all()
    
    # Exclude questions that should not be selected
    if exclude_question_ids:
        all_questions = all_questions.exclude(id__in=exclude_question_ids)
    
    logger.info(f"Total available questions after exclusions: {all_questions.count()}")
    
    # Get student's answer history for these questions
    student_answers = TestAnswer.objects.filter(
        session__student_id=student_id,
        question__in=all_questions,
        session__is_completed=True
    ).select_related('question')
    
    # Categorize questions into buckets
    answered_question_ids = set()
    correct_question_ids = set()
    wrong_unanswered_question_ids = set()
    
    for answer in student_answers:
        answered_question_ids.add(answer.question.id)
        if answer.is_correct:
            correct_question_ids.add(answer.question.id)
        else:
            # Either wrong answer or unanswered (selected_answer is None)
            wrong_unanswered_question_ids.add(answer.question.id)
    
    # Bucket A: Never attempted questions
    new_questions = all_questions.exclude(id__in=answered_question_ids)
    
    # Bucket B: Wrong/Unanswered questions
    wrong_questions = all_questions.filter(id__in=wrong_unanswered_question_ids)
    
    # Bucket C: Correctly answered questions
    correct_questions = all_questions.filter(id__in=correct_question_ids)
    
    logger.info(f"Question buckets - New: {new_questions.count()}, Wrong/Unanswered: {wrong_questions.count()}, Correct: {correct_questions.count()}")
    
    # Calculate target counts for each bucket
    target_new = int(question_count * ratio_new)
    target_wrong = int(question_count * ratio_wrong)
    target_correct = int(question_count * ratio_correct)
    
    # Adjust for rounding errors
    total_target = target_new + target_wrong + target_correct
    if total_target < question_count:
        # Add remaining to the new questions bucket (highest priority)
        target_new += question_count - total_target
    
    logger.info(f"Target allocation - New: {target_new}, Wrong/Unanswered: {target_wrong}, Correct: {target_correct}")
    
    # Select questions from each bucket
    selected_questions = []
    
    # Step 1: Try to fill each bucket with its target count
    actual_new = min(target_new, new_questions.count())
    actual_wrong = min(target_wrong, wrong_questions.count())
    actual_correct = min(target_correct, correct_questions.count())
    
    # Add questions from each bucket
    if actual_new > 0:
        selected_new = list(new_questions.order_by('?')[:actual_new])
        selected_questions.extend(selected_new)
        logger.info(f"Selected {len(selected_new)} new questions")
    
    if actual_wrong > 0:
        selected_wrong = list(wrong_questions.order_by('?')[:actual_wrong])
        selected_questions.extend(selected_wrong)
        logger.info(f"Selected {len(selected_wrong)} wrong/unanswered questions")
    
    if actual_correct > 0:
        selected_correct = list(correct_questions.order_by('?')[:actual_correct])
        selected_questions.extend(selected_correct)
        logger.info(f"Selected {len(selected_correct)} correct questions")
    
    # Step 2: Handle shortages with fallback logic
    current_count = len(selected_questions)
    remaining_needed = question_count - current_count
    
    if remaining_needed > 0:
        logger.info(f"Need {remaining_needed} more questions, applying fallback logic")
        
        # Get IDs of already selected questions
        selected_ids = {q.id for q in selected_questions}
        
        # Fallback priority order based on bucket shortages
        fallback_buckets = []
        
        # If new questions bucket was short, prioritize wrong then correct
        if actual_new < target_new:
            shortage_new = target_new - actual_new
            remaining_wrong = wrong_questions.exclude(id__in=selected_ids)
            remaining_correct = correct_questions.exclude(id__in=selected_ids)
            
            # Fill from wrong questions first
            if remaining_wrong.exists() and shortage_new > 0:
                take_from_wrong = min(shortage_new, remaining_wrong.count())
                fallback_wrong = list(remaining_wrong.order_by('?')[:take_from_wrong])
                selected_questions.extend(fallback_wrong)
                selected_ids.update(q.id for q in fallback_wrong)
                remaining_needed -= len(fallback_wrong)
                logger.info(f"Fallback: Added {len(fallback_wrong)} from wrong bucket for new shortage")
            
            # Fill remaining from correct questions
            if remaining_correct.exists() and remaining_needed > 0:
                remaining_correct = remaining_correct.exclude(id__in=selected_ids)
                take_from_correct = min(remaining_needed, remaining_correct.count())
                fallback_correct = list(remaining_correct.order_by('?')[:take_from_correct])
                selected_questions.extend(fallback_correct)
                selected_ids.update(q.id for q in fallback_correct)
                remaining_needed -= len(fallback_correct)
                logger.info(f"Fallback: Added {len(fallback_correct)} from correct bucket for new shortage")
        
        # If wrong questions bucket was short, prioritize new then correct
        if actual_wrong < target_wrong and remaining_needed > 0:
            shortage_wrong = target_wrong - actual_wrong
            remaining_new = new_questions.exclude(id__in=selected_ids)
            remaining_correct = correct_questions.exclude(id__in=selected_ids)
            
            # Fill from new questions first
            if remaining_new.exists() and shortage_wrong > 0:
                take_from_new = min(min(shortage_wrong, remaining_needed), remaining_new.count())
                fallback_new = list(remaining_new.order_by('?')[:take_from_new])
                selected_questions.extend(fallback_new)
                selected_ids.update(q.id for q in fallback_new)
                remaining_needed -= len(fallback_new)
                logger.info(f"Fallback: Added {len(fallback_new)} from new bucket for wrong shortage")
            
            # Fill remaining from correct questions
            if remaining_correct.exists() and remaining_needed > 0:
                remaining_correct = remaining_correct.exclude(id__in=selected_ids)
                take_from_correct = min(remaining_needed, remaining_correct.count())
                fallback_correct = list(remaining_correct.order_by('?')[:take_from_correct])
                selected_questions.extend(fallback_correct)
                selected_ids.update(q.id for q in fallback_correct)
                remaining_needed -= len(fallback_correct)
                logger.info(f"Fallback: Added {len(fallback_correct)} from correct bucket for wrong shortage")
        
        # If correct questions bucket was short, prioritize wrong then new
        if actual_correct < target_correct and remaining_needed > 0:
            shortage_correct = target_correct - actual_correct
            remaining_wrong = wrong_questions.exclude(id__in=selected_ids)
            remaining_new = new_questions.exclude(id__in=selected_ids)
            
            # Fill from wrong questions first
            if remaining_wrong.exists() and shortage_correct > 0:
                take_from_wrong = min(min(shortage_correct, remaining_needed), remaining_wrong.count())
                fallback_wrong = list(remaining_wrong.order_by('?')[:take_from_wrong])
                selected_questions.extend(fallback_wrong)
                selected_ids.update(q.id for q in fallback_wrong)
                remaining_needed -= len(fallback_wrong)
                logger.info(f"Fallback: Added {len(fallback_wrong)} from wrong bucket for correct shortage")
            
            # Fill remaining from new questions
            if remaining_new.exists() and remaining_needed > 0:
                remaining_new = remaining_new.exclude(id__in=selected_ids)
                take_from_new = min(remaining_needed, remaining_new.count())
                fallback_new = list(remaining_new.order_by('?')[:take_from_new])
                selected_questions.extend(fallback_new)
                selected_ids.update(q.id for q in fallback_new)
                remaining_needed -= len(fallback_new)
                logger.info(f"Fallback: Added {len(fallback_new)} from new bucket for correct shortage")
    
    # Final check: if we still need more questions, take from any remaining
    if remaining_needed > 0:
        selected_ids = {q.id for q in selected_questions}
        remaining_questions = all_questions.exclude(id__in=selected_ids)
        if remaining_questions.exists():
            final_questions = list(remaining_questions.order_by('?')[:remaining_needed])
            selected_questions.extend(final_questions)
            logger.info(f"Final fallback: Added {len(final_questions)} from any remaining questions")
    
    final_count = len(selected_questions)
    logger.info(f"Adaptive selection completed: {final_count} questions selected")
    
    # Convert to queryset and apply mathematical text cleaning
    if selected_questions:
        question_ids = [q.id for q in selected_questions]
        questions = Question.objects.filter(id__in=question_ids)
        
        # Apply the same mathematical text cleaning as the original function
        for question in questions:
            patterns_to_check = ['\\', '$', '^{', '_{', '\\frac', '\\sqrt', '\\alpha', '\\beta', '^ -', '^ +', '^-', '^+', 'x 10^', '\\mathrm', '\\text']
            needs_cleaning = any(pattern in question.question for pattern in patterns_to_check)
            if not needs_cleaning:
                all_options = question.option_a + question.option_b + question.option_c + question.option_d
                needs_cleaning = any(pattern in all_options for pattern in patterns_to_check)
            if not needs_cleaning and question.explanation:
                needs_cleaning = any(pattern in question.explanation for pattern in patterns_to_check)
            if not needs_cleaning and question.difficulty:
                needs_cleaning = any(pattern in question.difficulty for pattern in patterns_to_check)
            if not needs_cleaning and question.question_type:
                needs_cleaning = any(pattern in question.question_type for pattern in patterns_to_check)
            
            if needs_cleaning:
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                if question.explanation:
                    question.explanation = clean_mathematical_text(question.explanation)
                if question.difficulty:
                    question.difficulty = clean_mathematical_text(question.difficulty)
                if question.question_type:
                    question.question_type = clean_mathematical_text(question.question_type)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation', 'difficulty', 'question_type'])
        
        return questions
    else:
        return Question.objects.none()


def adaptive_generate_random_questions_from_database(question_count, student_id, exclude_question_ids=None):
    """
    Generate random questions from entire database using adaptive selection logic.
    Similar to adaptive_generate_questions_for_topics but selects from all subjects.
    
    Args:
        question_count (int): Total number of questions to select
        student_id (str): Student ID to check answer history
        exclude_question_ids (set): Question IDs to exclude from selection
        
    Returns:
        QuerySet: Selected questions following adaptive logic
    """
    logger.info(f"Adaptive random test generation for student {student_id}: {question_count} questions")
    
    # Use adaptive selection with all topics (empty list means all topics)
    return adaptive_generate_questions_for_topics(
        selected_topics=[],  # Empty list for all topics
        question_count=question_count,
        student_id=student_id,
        exclude_question_ids=exclude_question_ids
    )

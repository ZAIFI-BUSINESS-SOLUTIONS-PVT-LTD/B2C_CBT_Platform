"""
Rule-Based Question Selection Engine

This module implements a 14-rule engine for intelligent question selection
across different test types (topic-based and random tests).

The engine applies rules at two levels:
1. Session-level: Applied during test creation (R6, R7, R9, R14)
2. Question-level: Applied dynamically during selection (R1-R5, R10-R13)

Rules:
- R1: Accuracy-based recommendations (<60% accuracy)
- R2: Immediate simpler questions after incorrect answers (highest priority)
- R3: Harder questions after consecutive correct answers
- R4: Time-based easier questions (>120s average)
- R5: Harder questions for fast but inaccurate answers (<60s + <60% accuracy)
- R6: Difficulty distribution (30% Easy, 40% Moderate, 30% Hard)
- R7: NEET subject distribution (Physics, Chemistry, Biology)
- R8: Exclude questions seen within last 15 days
- R9: Include high-weightage topics
- R10: Skip similar easy questions after "too easy" feedback
- R11: Insert easier bridge questions after "too hard" feedback
- R12: Harder challenge after 3 consecutive correct
- R13: Easy confidence boost after 3 consecutive incorrect
- R14: Weak/strong topic allocation (70%/20%/10%)
"""

import logging
import random
from typing import List, Set, Dict, Any, Optional, Tuple, Union
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Q, Count, Avg, QuerySet
from django.utils import timezone

from ..models import Question, TestAnswer, Topic, TestSession, StudentProfile
from ..views.utils import clean_mathematical_text

logger = logging.getLogger(__name__)

# Configuration
NEET_SETTINGS = getattr(settings, "NEET_SETTINGS", {})

# Engine configuration
USE_RULE_ENGINE = NEET_SETTINGS.get("USE_RULE_ENGINE", True)
DYNAMIC_SELECTION_MODE = NEET_SETTINGS.get("DYNAMIC_SELECTION_MODE", False)

# High-weightage topics (configurable)
HIGH_WEIGHT_TOPICS = NEET_SETTINGS.get("HIGH_WEIGHT_TOPICS", [
    "Human Physiology", "Organic Chemistry", "Mechanics",
    "Coordination Compounds", "Thermodynamics", "Genetics"
])

# Subject mappings
NEET_SUBJECTS = {
    "Physics": ["Physics"],
    "Chemistry": ["Chemistry"], 
    "Biology": ["Botany", "Zoology"]
}

# Difficulty mappings
DIFFICULTY_LEVELS = ["Easy", "Moderate", "Hard"]
DIFFICULTY_DISTRIBUTION = {"Easy": 0.30, "Moderate": 0.40, "Hard": 0.30}

# Rule thresholds
ACCURACY_THRESHOLD = 60  # R1, R5
TIME_THRESHOLD_SLOW = 120  # R4 (seconds)
TIME_THRESHOLD_FAST = 60   # R5 (seconds)
CONSECUTIVE_STREAK = 3     # R3, R12, R13
EXCLUSION_DAYS = 15        # R8

# Weak/strong allocation ratios (R14)
WEAK_STRONG_RATIOS = {
    "weak": 0.70,
    "strong": 0.20,
    "random": 0.10
}


class SelectionEngine:
    """
    Main rule-based selection engine for question generation.
    """
    
    def __init__(self, student_id: Optional[str] = None, session_id: Optional[int] = None):
        """
        Initialize the selection engine.
        
        Args:
            student_id: Student ID for personalized selection
            session_id: Current test session ID for dynamic mode
        """
        self.student_id = student_id
        self.session_id = session_id
        self.logger = logger
        
    def generate_questions(self, 
                          selected_topics: List[int],
                          question_count: int,
                          test_type: str = "topic",
                          exclude_question_ids: Optional[Set[int]] = None,
                          difficulty_distribution: Optional[Dict[str, float]] = None) -> QuerySet:
        """
        Main entry point for question generation using rule-based engine.
        
        Args:
            selected_topics: List of topic IDs (empty for random tests)
            question_count: Number of questions to generate
            test_type: Type of test ("topic", "random")
            exclude_question_ids: Questions to exclude
            difficulty_distribution: Override default difficulty distribution
            
        Returns:
            QuerySet of selected Question objects
        """
        self.logger.info(f"Starting rule-based selection: {question_count} questions, "
                        f"test_type={test_type}, topics={len(selected_topics)}")
        
        try:
            # Apply session-level orchestration
            selected_question_ids = self._session_level_orchestration(
                selected_topics=selected_topics,
                question_count=question_count,
                test_type=test_type,
                exclude_question_ids=exclude_question_ids or set(),
                difficulty_distribution=difficulty_distribution
            )
            
            # Get Question objects and clean mathematical text
            if selected_question_ids:
                questions = Question.objects.filter(id__in=selected_question_ids)
                questions = self._clean_questions(questions)
                
                self.logger.info(f"Selection completed: {len(selected_question_ids)} questions selected")
                return questions
            else:
                self.logger.warning("No questions selected by rule engine")
                return Question.objects.none()
                
        except Exception as e:
            self.logger.exception(f"Rule engine failed: {e}")
            raise
    
    def _session_level_orchestration(self,
                                   selected_topics: List[int],
                                   question_count: int,
                                   test_type: str,
                                   exclude_question_ids: Set[int],
                                   difficulty_distribution: Optional[Dict[str, float]]) -> List[int]:
        """
        Apply session-level rules for question allocation.
        
        Returns:
            List of selected question IDs
        """
        # R8: Apply exclusion first
        available_questions = self._apply_exclusion_rule(
            selected_topics, exclude_question_ids, test_type
        )
        
        if not available_questions:
            self.logger.warning("No questions available after exclusion")
            return []
        
        # R7: Apply subject distribution for full tests
        subject_allocation = self._apply_subject_distribution(question_count, test_type)
        
        # R14: Apply weak/strong topic allocation within subjects
        topic_allocation = self._apply_weak_strong_allocation(
            selected_topics, subject_allocation, test_type
        )
        
        # R6: Apply difficulty distribution
        difficulty_dist = difficulty_distribution or DIFFICULTY_DISTRIBUTION
        difficulty_allocation = self._apply_difficulty_distribution(
            question_count, difficulty_dist
        )
        
        # Select questions based on allocations
        selected_ids = self._select_questions_by_allocation(
            available_questions=available_questions,
            topic_allocation=topic_allocation,
            subject_allocation=subject_allocation,
            difficulty_allocation=difficulty_allocation,
            question_count=question_count
        )
        
        # R9: Ensure high-weightage topics
        selected_ids = self._ensure_high_weight_topics(selected_ids, available_questions)
        
        return selected_ids
    
    def _apply_exclusion_rule(self, 
                             selected_topics: List[int],
                             exclude_question_ids: Set[int],
                             test_type: str) -> QuerySet:
        """
        R8: Exclude questions seen within last 15 days.
        """
        # Get base question pool
        if test_type == "random" or not selected_topics:
            base_questions = Question.objects.all()
        else:
            base_questions = Question.objects.filter(topic_id__in=selected_topics)
        
        # Add recent questions to exclusion if student_id provided
        all_exclusions = set(exclude_question_ids)
        if self.student_id:
            recent_questions = self._get_recent_question_ids()
            all_exclusions.update(recent_questions)
        
        # Apply exclusions
        if all_exclusions:
            available_questions = base_questions.exclude(id__in=all_exclusions)
            excluded_count = len(all_exclusions)
        else:
            available_questions = base_questions
            excluded_count = 0
        
        self.logger.info(f"Exclusion applied: {excluded_count} questions excluded, "
                        f"{available_questions.count()} available")
        
        return available_questions
    
    def _get_recent_question_ids(self) -> Set[int]:
        """
        Get questions seen by student in last 15 days.
        """
        cutoff_date = timezone.now() - timedelta(days=EXCLUSION_DAYS)
        
        # Use TestAnswer.answered_at to determine when the question was seen/answered.
        # The TestSession model does not define created_at in the current schema,
        # so filtering on answered_at is more precise for "seen within last N days" (R8).
        recent_answers = TestAnswer.objects.filter(
            session__student_id=self.student_id,
            answered_at__gte=cutoff_date,
            session__is_completed=True
        ).values_list('question_id', flat=True)

        return set(recent_answers)
    
    def _apply_subject_distribution(self, question_count: int, test_type: str) -> Dict[str, int]:
        """
        R7: Apply NEET subject distribution for full-length tests.
        """
        if question_count >= 150:  # Full-length test
            # Standard NEET distribution: 45 Physics, 45 Chemistry, 90 Biology
            allocation = {
                "Physics": 45,
                "Chemistry": 45,
                "Biology": 90
            }
        else:
            # Proportional scaling for smaller tests
            total_ratio = 45 + 45 + 90  # 180
            physics_ratio = 45 / total_ratio
            chemistry_ratio = 45 / total_ratio
            biology_ratio = 90 / total_ratio
            
            allocation = {
                "Physics": max(1, round(question_count * physics_ratio)),
                "Chemistry": max(1, round(question_count * chemistry_ratio)),
                "Biology": max(1, round(question_count * biology_ratio))
            }
            
            # Adjust for rounding errors
            total_allocated = sum(allocation.values())
            diff = question_count - total_allocated
            
            if diff > 0:
                # Add remainder to Biology (largest subject)
                allocation["Biology"] += diff
            elif diff < 0:
                # Remove from Biology first, then others
                if allocation["Biology"] > abs(diff):
                    allocation["Biology"] += diff
                else:
                    allocation["Biology"] = max(1, allocation["Biology"] + diff // 3)
                    allocation["Physics"] = max(1, allocation["Physics"] + diff // 3)
                    allocation["Chemistry"] = max(1, allocation["Chemistry"] + diff // 3)
        
        self.logger.info(f"Subject allocation: {allocation}")
        return allocation
    
    def _apply_weak_strong_allocation(self,
                                    selected_topics: List[int],
                                    subject_allocation: Dict[str, int],
                                    test_type: str) -> Dict[str, Dict[str, int]]:
        """
        R14: Allocate questions by student's topic performance (70% weak, 20% strong, 10% random).
        """
        if not self.student_id:
            # No student history, use random allocation
            return self._random_topic_allocation(selected_topics, subject_allocation, test_type)
        
        # Get topic performance data
        topic_performance = self._get_topic_performance()
        
        allocation = {}
        for subject, count in subject_allocation.items():
            subject_topics = self._get_topics_for_subject(subject, selected_topics, test_type)
            
            if not subject_topics:
                allocation[subject] = {"random": count}
                continue
            
            # Calculate allocation counts
            weak_count = max(1, round(count * WEAK_STRONG_RATIOS["weak"]))
            strong_count = max(1, round(count * WEAK_STRONG_RATIOS["strong"]))
            random_count = count - weak_count - strong_count
            
            # Categorize topics by performance
            weak_topics, strong_topics = self._categorize_topics_by_performance(
                subject_topics, topic_performance
            )
            
            allocation[subject] = {
                "weak": min(weak_count, len(weak_topics)),
                "strong": min(strong_count, len(strong_topics)),
                "random": max(0, random_count)
            }
            
            # Redistribute if insufficient topics in categories
            total_categorized = allocation[subject]["weak"] + allocation[subject]["strong"]
            if total_categorized < count:
                allocation[subject]["random"] = count - total_categorized
        
        self.logger.info(f"Weak/strong allocation: {allocation}")
        return allocation
    
    def _get_topic_performance(self) -> Dict[int, float]:
        """
        Calculate student's accuracy per topic.
        """
        if not self.student_id:
            return {}
        
        # Get completed test answers grouped by topic
        # Annotate average time taken per topic as well (for R4/R5 timing rules)
        topic_stats = TestAnswer.objects.filter(
            session__student_id=self.student_id,
            session__is_completed=True,
            selected_answer__isnull=False
        ).values('question__topic_id').annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
            avg_time=Avg('time_taken')
        )

        performance = {}
        # Store per-topic average time for use by timing rules
        self.topic_time_stats = {}

        for stat in topic_stats:
            topic_id = stat['question__topic_id']
            if stat['total'] > 0:
                accuracy = (stat['correct'] / stat['total']) * 100
                performance[topic_id] = accuracy
                # avg_time may be None if no time_taken recorded
                try:
                    avg_time = float(stat.get('avg_time')) if stat.get('avg_time') is not None else None
                except Exception:
                    avg_time = None
                self.topic_time_stats[topic_id] = avg_time

        return performance
    
    def _categorize_topics_by_performance(self,
                                        topics: List[int],
                                        performance: Dict[int, float]) -> Tuple[List[int], List[int]]:
        """
        Categorize topics as weak (<60% accuracy) or strong (>=60% accuracy).
        """
        weak_topics = []
        strong_topics = []
        
        for topic_id in topics:
            accuracy = performance.get(topic_id, 0)  # Default to 0 for new topics
            if accuracy < ACCURACY_THRESHOLD:
                weak_topics.append(topic_id)
            else:
                strong_topics.append(topic_id)
        
        return weak_topics, strong_topics
    
    def _apply_difficulty_distribution(self,
                                     question_count: int,
                                     difficulty_dist: Dict[str, float]) -> Dict[str, int]:
        """
        R6: Apply difficulty distribution (default: 30% Easy, 40% Moderate, 30% Hard).
        """
        allocation = {}
        total_allocated = 0
        
        for difficulty, ratio in difficulty_dist.items():
            count = max(1, round(question_count * ratio))
            allocation[difficulty] = count
            total_allocated += count
        
        # Adjust for rounding errors
        diff = question_count - total_allocated
        if diff != 0:
            # Add/subtract from Moderate (largest proportion)
            allocation["Moderate"] = max(1, allocation.get("Moderate", 0) + diff)
        
        self.logger.info(f"Difficulty allocation: {allocation}")
        return allocation
    
    def _select_questions_by_allocation(self,
                                      available_questions: QuerySet,
                                      topic_allocation: Dict[str, Dict[str, int]],
                                      subject_allocation: Dict[str, int],
                                      difficulty_allocation: Dict[str, int],
                                      question_count: int) -> List[int]:
        """
        Select questions based on all allocation rules.
        """
        selected_ids = []
        
        # Track remaining allocations
        remaining_difficulty = difficulty_allocation.copy()
        
        for subject, subject_count in subject_allocation.items():
            subject_questions = self._filter_questions_by_subject(available_questions, subject)
            
            if not subject_questions.exists():
                self.logger.warning(f"No questions available for subject: {subject}")
                continue
            
            # Get topic allocation for this subject
            topic_alloc = topic_allocation.get(subject, {"random": subject_count})
            
            # Select questions for each topic category
            for category, count in topic_alloc.items():
                if count <= 0:
                    continue
                
                category_questions = self._get_questions_for_category(
                    subject_questions, category, subject
                )
                
                # Apply difficulty distribution within category
                category_ids = self._select_with_difficulty_balance(
                    category_questions, count, remaining_difficulty
                )
                
                selected_ids.extend(category_ids)
                
                # Update remaining difficulty counts
                for question_id in category_ids:
                    question = category_questions.filter(id=question_id).first()
                    if question and question.difficulty:
                        difficulty = self._normalize_difficulty(question.difficulty)
                        if difficulty in remaining_difficulty and remaining_difficulty[difficulty] > 0:
                            remaining_difficulty[difficulty] -= 1
        
        # Fill remaining slots if needed
        if len(selected_ids) < question_count:
            remaining_count = question_count - len(selected_ids)
            remaining_questions = available_questions.exclude(id__in=selected_ids)
            additional_ids = self._select_additional_questions(
                remaining_questions, remaining_count, remaining_difficulty
            )
            selected_ids.extend(additional_ids)
        
        # Ensure we don't exceed requested count
        if len(selected_ids) > question_count:
            selected_ids = selected_ids[:question_count]
        
        self.logger.info(f"Final selection: {len(selected_ids)} questions")
        return selected_ids
    
    def _ensure_high_weight_topics(self, 
                                 selected_ids: List[int],
                                 available_questions: QuerySet) -> List[int]:
        """
        R9: Ensure at least 1 question from high-weightage topics.
        """
        if not HIGH_WEIGHT_TOPICS:
            return selected_ids
        
        # Check if any selected questions are from high-weight topics
        selected_questions = Question.objects.filter(id__in=selected_ids)
        selected_topics = set(selected_questions.values_list('topic__name', flat=True))
        
        high_weight_covered = any(topic in selected_topics for topic in HIGH_WEIGHT_TOPICS)
        
        if not high_weight_covered:
            # Find available high-weight questions
            high_weight_questions = available_questions.filter(
                topic__name__in=HIGH_WEIGHT_TOPICS
            ).exclude(id__in=selected_ids)
            
            if high_weight_questions.exists():
                # Replace one random question with a high-weight one
                if selected_ids:
                    # Remove one question (prefer from over-represented subjects)
                    selected_ids.pop()
                
                # Add one high-weight question
                high_weight_q = high_weight_questions.order_by('?').first()
                selected_ids.append(high_weight_q.id)
                
                self.logger.info(f"Added high-weight topic question: {high_weight_q.topic.name}")
        
        return selected_ids
    
    # Helper methods
    
    def _get_topics_for_subject(self, subject: str, selected_topics: List[int], test_type: str) -> List[int]:
        """Get topic IDs for a specific subject."""
        if test_type == "random" or not selected_topics:
            # Get all topics for this subject
            subject_names = NEET_SUBJECTS.get(subject, [subject])
            topics = Topic.objects.filter(subject__in=subject_names).values_list('id', flat=True)
            return list(topics)
        else:
            # Filter selected topics by subject
            subject_names = NEET_SUBJECTS.get(subject, [subject])
            topics = Topic.objects.filter(
                id__in=selected_topics,
                subject__in=subject_names
            ).values_list('id', flat=True)
            return list(topics)
    
    def _filter_questions_by_subject(self, questions: QuerySet, subject: str) -> QuerySet:
        """Filter questions by subject."""
        subject_names = NEET_SUBJECTS.get(subject, [subject])
        return questions.filter(topic__subject__in=subject_names)
    
    def _get_questions_for_category(self, questions: QuerySet, category: str, subject: str) -> QuerySet:
        """Get questions for a specific category (weak/strong/random)."""
        if category == "random":
            return questions
        
        # Get topic IDs for this category
        topic_performance = self._get_topic_performance()
        subject_topics = list(questions.values_list('topic_id', flat=True).distinct())
        
        if category == "weak":
            weak_topics, _ = self._categorize_topics_by_performance(subject_topics, topic_performance)
            return questions.filter(topic_id__in=weak_topics)
        elif category == "strong":
            _, strong_topics = self._categorize_topics_by_performance(subject_topics, topic_performance)
            return questions.filter(topic_id__in=strong_topics)
        
        return questions
    
    def _select_with_difficulty_balance(self,
                                      questions: QuerySet,
                                      count: int,
                                      remaining_difficulty: Dict[str, int]) -> List[int]:
        """Select questions while maintaining difficulty balance."""
        if not questions.exists() or count <= 0:
            return []
        
        # Group questions by difficulty
        difficulty_groups = {}
        for difficulty in DIFFICULTY_LEVELS:
            difficulty_groups[difficulty] = questions.filter(
                difficulty__icontains=difficulty
            ).values_list('id', flat=True)
        
        # Add unknown difficulty questions
        known_ids = set()
        for ids in difficulty_groups.values():
            known_ids.update(ids)
        
        unknown_questions = questions.exclude(id__in=known_ids).values_list('id', flat=True)
        difficulty_groups["Unknown"] = unknown_questions
        
        # Select questions trying to maintain difficulty balance
        selected = []
        
        # First, try to use remaining difficulty allocations
        for difficulty, remaining in remaining_difficulty.items():
            if remaining > 0 and len(selected) < count:
                available_ids = list(difficulty_groups.get(difficulty, []))
                if available_ids:
                    take_count = min(remaining, len(available_ids), count - len(selected))
                    random.shuffle(available_ids)
                    selected.extend(available_ids[:take_count])
        
        # Fill remaining slots with any available questions
        if len(selected) < count:
            all_available_ids = set()
            for ids in difficulty_groups.values():
                all_available_ids.update(ids)
            
            remaining_ids = list(all_available_ids - set(selected))
            if remaining_ids:
                random.shuffle(remaining_ids)
                needed = count - len(selected)
                selected.extend(remaining_ids[:needed])
        
        return selected[:count]
    
    def _select_additional_questions(self,
                                   questions: QuerySet,
                                   count: int,
                                   remaining_difficulty: Dict[str, int]) -> List[int]:
        """Select additional questions to fill remaining slots."""
        if not questions.exists() or count <= 0:
            return []
        
        available_ids = list(questions.values_list('id', flat=True))
        if len(available_ids) <= count:
            return available_ids
        
        random.shuffle(available_ids)
        return available_ids[:count]
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """Normalize difficulty labels."""
        if not difficulty:
            return "Unknown"
        
        difficulty_lower = difficulty.lower()
        if "easy" in difficulty_lower:
            return "Easy"
        elif "moderate" in difficulty_lower or "medium" in difficulty_lower:
            return "Moderate"
        elif "hard" in difficulty_lower or "difficult" in difficulty_lower:
            return "Hard"
        else:
            return "Unknown"
    
    def _random_topic_allocation(self,
                               selected_topics: List[int],
                               subject_allocation: Dict[str, int],
                               test_type: str) -> Dict[str, Dict[str, int]]:
        """Fallback allocation when no student history available."""
        allocation = {}
        for subject, count in subject_allocation.items():
            allocation[subject] = {"random": count}
        return allocation
    
    def _clean_questions(self, questions: QuerySet) -> QuerySet:
        """Clean mathematical text in questions."""
        questions_list = list(questions)
        for question in questions_list:
            # Clean question text and options
            question.question = clean_mathematical_text(question.question)
            question.optionA = clean_mathematical_text(question.optionA)
            question.optionB = clean_mathematical_text(question.optionB)
            question.optionC = clean_mathematical_text(question.optionC)
            question.optionD = clean_mathematical_text(question.optionD)
            if hasattr(question, 'explanation'):
                question.explanation = clean_mathematical_text(question.explanation)
            
            # Save cleaned question
            question.save()
        
        return questions


# Question-level adaptation helpers (for dynamic mode)

def apply_streak_rules(student_id: str, session: TestSession, recent_answers: List[TestAnswer]) -> Optional[List[int]]:
    """
    Apply R2, R3, R12, R13 based on recent answer patterns.
    
    Args:
        student_id: Student ID
        session: Current test session
        recent_answers: List of recent answers (most recent first)
        
    Returns:
        List of recommended question IDs or None
    """
    if not recent_answers:
        return None
    
    # R2: If last answer incorrect, recommend simpler questions from same sub-topic
    last_answer = recent_answers[0]
    if not last_answer.is_correct:
        logger.info(f"Applying R2: Last answer incorrect for student {student_id}")
        return _get_simpler_questions_same_topic(last_answer.question.topic_id, exclude_ids=[last_answer.question_id])
    
    # Check for streaks
    if len(recent_answers) >= CONSECUTIVE_STREAK:
        recent_correct = [ans.is_correct for ans in recent_answers[:CONSECUTIVE_STREAK]]
        
        # R12: 3 consecutive correct answers
        if all(recent_correct):
            logger.info(f"Applying R12: 3 consecutive correct for student {student_id}")
            return _get_harder_challenge_questions(recent_answers[0].question.topic_id)
        
        # R13: 3 consecutive incorrect answers
        if not any(recent_correct):
            logger.info(f"Applying R13: 3 consecutive incorrect for student {student_id}")
            return _get_confidence_boost_questions()
    
    # R3: 2-3 consecutive correct in same sub-topic
    if len(recent_answers) >= 2:
        last_two = recent_answers[:2]
        if (all(ans.is_correct for ans in last_two) and 
            last_two[0].question.topic_id == last_two[1].question.topic_id):
            logger.info(f"Applying R3: Consecutive correct in same topic for student {student_id}")
            return _get_harder_questions_same_topic(last_two[0].question.topic_id)
    
    return None

def _get_simpler_questions_same_topic(topic_id: int, exclude_ids: List[int]) -> List[int]:
    """Get simpler questions from the same topic."""
    questions = Question.objects.filter(
        topic_id=topic_id,
        difficulty__icontains="easy"
    ).exclude(id__in=exclude_ids).values_list('id', flat=True)
    
    return list(questions[:2])  # Return up to 2 simpler questions

def _get_harder_questions_same_topic(topic_id: int) -> List[int]:
    """Get harder questions from the same topic."""
    questions = Question.objects.filter(
        topic_id=topic_id,
        difficulty__icontains="hard"
    ).values_list('id', flat=True)
    
    return list(questions[:1])  # Return 1 harder question

def _get_harder_challenge_questions(topic_id: int) -> List[int]:
    """Get challenging questions for R12."""
    questions = Question.objects.filter(
        topic_id=topic_id,
        difficulty__icontains="hard"
    ).values_list('id', flat=True)
    
    return list(questions[:1])

def _get_confidence_boost_questions() -> List[int]:
    """Get easy questions for confidence boost."""
    questions = Question.objects.filter(
        difficulty__icontains="easy"
    ).order_by('?').values_list('id', flat=True)
    
    return list(questions[:1])


# Public interface functions

def generate_questions_with_rules(selected_topics: List[int],
                                question_count: int,
                                student_id: Optional[str] = None,
                                session_id: Optional[int] = None,
                                test_type: str = "topic",
                                exclude_question_ids: Optional[Set[int]] = None,
                                difficulty_distribution: Optional[Dict[str, float]] = None) -> QuerySet:
    """
    Public interface for rule-based question generation.
    
    Args:
        selected_topics: List of topic IDs (empty for random tests)
        question_count: Number of questions to generate
        student_id: Student ID for personalized selection
        session_id: Current test session ID
        test_type: Type of test ("topic", "random")
        exclude_question_ids: Questions to exclude
        difficulty_distribution: Override default difficulty distribution
        
    Returns:
        QuerySet of selected Question objects
    """
    if not USE_RULE_ENGINE:
        logger.info("Rule engine disabled, falling back to legacy selection")
        return None
    
    engine = SelectionEngine(student_id=student_id, session_id=session_id)
    return engine.generate_questions(
        selected_topics=selected_topics,
        question_count=question_count,
        test_type=test_type,
        exclude_question_ids=exclude_question_ids,
        difficulty_distribution=difficulty_distribution
    )
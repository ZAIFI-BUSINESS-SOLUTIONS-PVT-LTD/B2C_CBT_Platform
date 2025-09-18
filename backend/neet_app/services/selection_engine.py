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
DYNAMIC_SELECTION_MODE = NEET_SETTINGS.get("DYNAMIC_SELECTION_MODE", True)  # Enable by default
APPLY_TIMING_RULES = NEET_SETTINGS.get("APPLY_TIMING_RULES", True)  # R4, R5
APPLY_FEEDBACK_RULES = NEET_SETTINGS.get("APPLY_FEEDBACK_RULES", True)  # R10, R11
LEGACY_FALLBACK_ENABLED = NEET_SETTINGS.get("LEGACY_FALLBACK_ENABLED", True)

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
        Main entry point for question generation using comprehensive 14-rule engine.
        
        Args:
            selected_topics: List of topic IDs (empty for random tests)
            question_count: Number of questions to generate
            test_type: Type of test ("topic", "random")
            exclude_question_ids: Questions to exclude
            difficulty_distribution: Override default difficulty distribution
            
        Returns:
            QuerySet of selected Question objects
        """
        self.logger.info(f"Starting comprehensive rule-based selection: {question_count} questions, "
                        f"test_type={test_type}, topics={len(selected_topics)}")
        
        try:
            # Apply all 14 rules systematically with fallback
            selected_question_ids = self._apply_all_rules_systematically(
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
                self.logger.warning("No questions selected by any method")
                return Question.objects.none()
                
        except Exception as e:
            self.logger.exception(f"Complete selection failed: {e}")
            return Question.objects.none()
    
    def _apply_all_rules_systematically(self,
                                      selected_topics: List[int],
                                      question_count: int,
                                      test_type: str,
                                      exclude_question_ids: Set[int],
                                      difficulty_distribution: Optional[Dict[str, float]]) -> List[int]:
        """
        Apply all 14 rules systematically with proper fallback mechanisms.
        
        Returns:
            List of selected question IDs
        """
        selected_ids = []
        remaining_count = question_count
        all_exclusions = set(exclude_question_ids)
        
        # Phase 1: Apply dynamic streak rules (R2, R3, R12, R13) - highest priority
        if self.student_id and self.session_id:
            streak_ids = self._apply_dynamic_streak_rules(all_exclusions)
            if streak_ids:
                selected_ids.extend(streak_ids)
                all_exclusions.update(streak_ids)
                remaining_count -= len(streak_ids)
                self.logger.info(f"Phase 1 - Streak rules applied: {len(streak_ids)} questions selected")
        
        # Phase 2: Apply session-level rules with remaining count
        if remaining_count > 0:
            session_ids = self._apply_session_level_rules(
                selected_topics, remaining_count, test_type, all_exclusions, difficulty_distribution
            )
            if session_ids:
                selected_ids.extend(session_ids)
                all_exclusions.update(session_ids)
                remaining_count -= len(session_ids)
                self.logger.info(f"Phase 2 - Session rules applied: {len(session_ids)} questions selected")
        
        # Phase 3: Apply timing-based rules (R4, R5) if we still need more questions
        if remaining_count > 0 and self.student_id:
            timing_ids = self._apply_timing_rules(selected_topics, remaining_count, test_type, all_exclusions)
            if timing_ids:
                selected_ids.extend(timing_ids)
                all_exclusions.update(timing_ids)
                remaining_count -= len(timing_ids)
                self.logger.info(f"Phase 3 - Timing rules applied: {len(timing_ids)} questions selected")
        
        # Phase 4: Apply feedback-based rules (R10, R11) if available
        if remaining_count > 0 and self.student_id:
            feedback_ids = self._apply_feedback_rules(selected_topics, remaining_count, test_type, all_exclusions)
            if feedback_ids:
                selected_ids.extend(feedback_ids)
                all_exclusions.update(feedback_ids)
                remaining_count -= len(feedback_ids)
                self.logger.info(f"Phase 4 - Feedback rules applied: {len(feedback_ids)} questions selected")
        
        # Phase 5: Legacy fallback selection for remaining questions
        if remaining_count > 0:
            legacy_ids = self._legacy_fallback_selection(
                selected_topics, remaining_count, test_type, all_exclusions
            )
            if legacy_ids:
                selected_ids.extend(legacy_ids)
                self.logger.info(f"Phase 5 - Legacy fallback applied: {len(legacy_ids)} questions selected")
        
        # Final validation and truncation
        if len(selected_ids) > question_count:
            selected_ids = selected_ids[:question_count]
            self.logger.warning(f"Truncated selection to requested count: {question_count}")
        
        self.logger.info(f"Total questions selected: {len(selected_ids)}/{question_count}")
        return selected_ids
    
    def _apply_streak_rules(self) -> Optional[List[int]]:
        """
        Apply streak-based rules (R2, R3, R12, R13) when student and session data available.
        
        Returns:
            List of question IDs recommended by streak rules, or None if not applicable
        """
        # Check if dynamic selection mode is enabled
        if not DYNAMIC_SELECTION_MODE:
            return None
            
        if not self.student_id or not self.session_id:
            return None
            
        try:
            # Get the current session
            session = TestSession.objects.filter(
                id=self.session_id,
                student_id=self.student_id
            ).first()
            
            if not session:
                self.logger.warning(f"Session {self.session_id} not found for student {self.student_id}")
                return None
            
            # Get recent answers for this session (most recent first)
            # Limit to last 10 answers to avoid performance issues
            recent_answers = list(
                TestAnswer.objects.filter(
                    session=session,
                    selected_answer__isnull=False  # Only consider answered questions
                )
                .select_related('question', 'question__topic')
                .order_by('-answered_at')[:10]
            )
            
            if not recent_answers:
                self.logger.info("No recent answers found for streak rule application")
                return None
            
            # Apply streak rules
            streak_question_ids = apply_streak_rules(
                student_id=self.student_id,
                session=session,
                recent_answers=recent_answers
            )
            
            if streak_question_ids:
                self.logger.info(f"Streak rules applied: {len(streak_question_ids)} questions recommended")
                # Ensure questions exist and are available
                existing_ids = list(
                    Question.objects.filter(id__in=streak_question_ids)
                    .values_list('id', flat=True)
                )
                return existing_ids
            
            return None
            
        except Exception as e:
            self.logger.exception(f"Error applying streak rules: {e}")
            return None
    
    def _apply_dynamic_streak_rules(self, exclude_question_ids: Set[int]) -> List[int]:
        """
        Apply dynamic streak rules (R2, R3, R12, R13) based on recent answer patterns.
        
        Args:
            exclude_question_ids: Questions to exclude from selection
            
        Returns:
            List of question IDs selected by streak rules
        """
        if not self.student_id or not self.session_id:
            return []
            
        try:
            # Get current session and recent answers
            session = TestSession.objects.filter(id=self.session_id, student_id=self.student_id).first()
            if not session:
                return []
            
            # Get recent answers for this session (most recent first)
            recent_answers = list(TestAnswer.objects.filter(
                session=session,
                selected_answer__isnull=False  # Only answered questions
            ).select_related('question', 'question__topic').order_by('-answered_at')[:10])
            
            if not recent_answers:
                return []
            
            # Apply streak rules using the existing function
            streak_ids = apply_streak_rules(self.student_id, session, recent_answers)
            if not streak_ids:
                return []
            
            # Filter out excluded questions and validate availability
            available_streak_ids = []
            for qid in streak_ids:
                if qid not in exclude_question_ids:
                    # Verify question exists and is available
                    if Question.objects.filter(id=qid).exists():
                        available_streak_ids.append(qid)
            
            if available_streak_ids:
                self.logger.info(f"Dynamic streak rules applied: {len(available_streak_ids)} questions selected")
            
            return available_streak_ids
            
        except Exception as e:
            self.logger.warning(f"Failed to apply dynamic streak rules: {e}")
            return []
    
    def _apply_session_level_rules(self,
                                 selected_topics: List[int],
                                 question_count: int,
                                 test_type: str,
                                 exclude_question_ids: Set[int],
                                 difficulty_distribution: Optional[Dict[str, float]]) -> List[int]:
        """
        Apply session-level rules (R6, R7, R8, R9, R14, R1) using existing orchestration.
        
        Returns:
            List of question IDs selected by session-level rules
        """
        try:
            return self._session_level_orchestration(
                selected_topics=selected_topics,
                question_count=question_count,
                test_type=test_type,
                exclude_question_ids=exclude_question_ids,
                difficulty_distribution=difficulty_distribution
            )
        except Exception as e:
            self.logger.warning(f"Failed to apply session-level rules: {e}")
            return []
    
    def _apply_timing_rules(self,
                          selected_topics: List[int],
                          question_count: int,
                          test_type: str,
                          exclude_question_ids: Set[int]) -> List[int]:
        """
        Apply timing-based rules (R4, R5) to select questions based on student's time patterns.
        
        R4: Time-based easier questions (>120s average)
        R5: Harder questions for fast but inaccurate answers (<60s + <60% accuracy)
        
        Returns:
            List of question IDs selected by timing rules
        """
        if not self.student_id:
            return []
        
        try:
            # Get topic performance including timing data
            topic_performance = self._get_topic_performance()
            if not hasattr(self, 'topic_time_stats') or not self.topic_time_stats:
                return []
            
            # Get base question pool
            if test_type == "random" or not selected_topics:
                base_questions = Question.objects.all()
            else:
                base_questions = Question.objects.filter(topic_id__in=selected_topics)
            
            base_questions = base_questions.exclude(id__in=exclude_question_ids)
            
            timing_questions = []
            questions_needed = min(question_count, 3)  # Limit timing rule impact
            
            # R4: Easier questions for slow topics (>120s average)
            slow_topics = [
                topic_id for topic_id, avg_time in self.topic_time_stats.items()
                if avg_time and avg_time > TIME_THRESHOLD_SLOW
            ]
            
            if slow_topics:
                r4_questions = base_questions.filter(
                    topic_id__in=slow_topics,
                    difficulty__icontains="easy"
                ).values_list('id', flat=True)
                
                r4_count = min(len(r4_questions), questions_needed // 2)
                if r4_count > 0:
                    selected_r4 = list(r4_questions[:r4_count])
                    timing_questions.extend(selected_r4)
                    questions_needed -= len(selected_r4)
                    self.logger.info(f"R4 applied: {len(selected_r4)} easier questions for slow topics")
            
            # R5: Harder questions for fast but inaccurate topics (<60s + <60% accuracy)
            if questions_needed > 0:
                fast_inaccurate_topics = [
                    topic_id for topic_id, avg_time in self.topic_time_stats.items()
                    if (avg_time and avg_time < TIME_THRESHOLD_FAST and 
                        topic_performance.get(topic_id, 0) < ACCURACY_THRESHOLD)
                ]
                
                if fast_inaccurate_topics:
                    r5_questions = base_questions.filter(
                        topic_id__in=fast_inaccurate_topics,
                        difficulty__icontains="hard"
                    ).exclude(id__in=timing_questions).values_list('id', flat=True)
                    
                    r5_count = min(len(r5_questions), questions_needed)
                    if r5_count > 0:
                        selected_r5 = list(r5_questions[:r5_count])
                        timing_questions.extend(selected_r5)
                        self.logger.info(f"R5 applied: {len(selected_r5)} harder questions for fast-inaccurate topics")
            
            return timing_questions
            
        except Exception as e:
            self.logger.warning(f"Failed to apply timing rules: {e}")
            return []
    
    def _apply_feedback_rules(self,
                            selected_topics: List[int],
                            question_count: int,
                            test_type: str,
                            exclude_question_ids: Set[int]) -> List[int]:
        """
        Apply feedback-based rules (R10, R11) based on student feedback patterns.
        
        R10: Skip similar easy questions after "too easy" feedback
        R11: Insert easier bridge questions after "too hard" feedback
        
        Note: This is a placeholder implementation as feedback data model is not defined.
        In a complete implementation, you would need a StudentFeedback model.
        
        Returns:
            List of question IDs selected by feedback rules
        """
        try:
            # Placeholder implementation - would need feedback data
            # For now, just apply some basic adaptive logic
            
            if not self.student_id:
                return []
            
            # Get base question pool
            if test_type == "random" or not selected_topics:
                base_questions = Question.objects.all()
            else:
                base_questions = Question.objects.filter(topic_id__in=selected_topics)
            
            base_questions = base_questions.exclude(id__in=exclude_question_ids)
            
            # R11: Add some easier bridge questions if student has low overall accuracy
            topic_performance = self._get_topic_performance()
            if topic_performance:
                overall_accuracy = sum(topic_performance.values()) / len(topic_performance)
                if overall_accuracy < 40:  # Very low accuracy
                    bridge_questions = base_questions.filter(
                        difficulty__icontains="easy"
                    ).values_list('id', flat=True)
                    
                    bridge_count = min(len(bridge_questions), min(question_count, 2))
                    if bridge_count > 0:
                        selected_bridge = list(bridge_questions[:bridge_count])
                        self.logger.info(f"R11 applied: {len(selected_bridge)} bridge questions for low accuracy")
                        return selected_bridge
            
            return []
            
        except Exception as e:
            self.logger.warning(f"Failed to apply feedback rules: {e}")
            return []
    
    def _legacy_fallback_selection(self,
                                 selected_topics: List[int],
                                 question_count: int,
                                 test_type: str,
                                 exclude_question_ids: Set[int]) -> List[int]:
        """
        Fallback to simple random selection when rule-based methods don't produce enough questions.
        
        Args:
            selected_topics: List of topic IDs
            question_count: Number of questions needed
            test_type: Type of test
            exclude_question_ids: Questions to exclude
            
        Returns:
            List of question IDs from legacy selection
        """
        try:
            self.logger.info(f"Applying legacy fallback for {question_count} questions")
            
            # Get base question pool
            if test_type == "random" or not selected_topics:
                questions = Question.objects.all()
            else:
                questions = Question.objects.filter(topic_id__in=selected_topics)
            
            # Apply exclusions
            if exclude_question_ids:
                questions = questions.exclude(id__in=exclude_question_ids)
            
            # Get available question IDs
            available_ids = list(questions.values_list('id', flat=True))
            
            if not available_ids:
                self.logger.warning("No questions available for legacy fallback")
                return []
            
            # Shuffle and select up to question_count
            random.shuffle(available_ids)
            selected_count = min(len(available_ids), question_count)
            
            return available_ids[:selected_count]
            
        except Exception as e:
            self.logger.error(f"Legacy fallback failed: {e}")
            return []
    
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
        """Select questions while maintaining difficulty balance with fallback logic."""
        if not questions.exists() or count <= 0:
            return []
        
        # Group questions by difficulty
        difficulty_groups = {}
        for difficulty in DIFFICULTY_LEVELS:
            difficulty_groups[difficulty] = list(questions.filter(
                difficulty__icontains=difficulty
            ).values_list('id', flat=True))
        
        # Add unknown difficulty questions
        known_ids = set()
        for ids in difficulty_groups.values():
            known_ids.update(ids)
        
        unknown_questions = list(questions.exclude(id__in=known_ids).values_list('id', flat=True))
        difficulty_groups["Unknown"] = unknown_questions
        
        # Define difficulty fallback hierarchy: Hard -> Moderate -> Easy -> Unknown
        difficulty_fallback = {
            "Hard": ["Hard", "Moderate", "Easy", "Unknown"],
            "Moderate": ["Moderate", "Easy", "Hard", "Unknown"], 
            "Easy": ["Easy", "Moderate", "Hard", "Unknown"],
            "Unknown": ["Unknown", "Easy", "Moderate", "Hard"]
        }
        
        selected = []
        selection_log = []
        
        # First, try to use remaining difficulty allocations with fallback
        for difficulty, remaining in remaining_difficulty.items():
            if remaining > 0 and len(selected) < count:
                fallback_levels = difficulty_fallback.get(difficulty, [difficulty])
                questions_selected_for_difficulty = 0
                
                for fallback_level in fallback_levels:
                    if questions_selected_for_difficulty >= remaining or len(selected) >= count:
                        break
                        
                    available_ids = [qid for qid in difficulty_groups.get(fallback_level, []) 
                                   if qid not in selected]
                    
                    if available_ids:
                        take_count = min(
                            remaining - questions_selected_for_difficulty,
                            len(available_ids), 
                            count - len(selected)
                        )
                        random.shuffle(available_ids)
                        selected_batch = available_ids[:take_count]
                        selected.extend(selected_batch)
                        questions_selected_for_difficulty += len(selected_batch)
                        
                        if fallback_level != difficulty:
                            selection_log.append(f"Difficulty fallback: {difficulty} -> {fallback_level}, selected {len(selected_batch)} questions")
                        else:
                            selection_log.append(f"Direct selection: {difficulty}, selected {len(selected_batch)} questions")
        
        # Fill remaining slots with any available questions
        if len(selected) < count:
            all_available_ids = set()
            for ids in difficulty_groups.values():
                all_available_ids.update(ids)
            
            remaining_ids = list(all_available_ids - set(selected))
            if remaining_ids:
                random.shuffle(remaining_ids)
                needed = count - len(selected)
                additional_selected = remaining_ids[:needed]
                selected.extend(additional_selected)
                selection_log.append(f"Additional fill: selected {len(additional_selected)} questions from any difficulty")
        
        # Log the selection process
        if selection_log:
            self.logger.info(f"Difficulty selection log: {'; '.join(selection_log)}")
        
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
            # Use same field names as models (option_a, option_b, option_c, option_d)
            question.question = clean_mathematical_text(question.question)
            # protect against missing option fields though model defines them
            if hasattr(question, 'option_a'):
                question.option_a = clean_mathematical_text(question.option_a)
            if hasattr(question, 'option_b'):
                question.option_b = clean_mathematical_text(question.option_b)
            if hasattr(question, 'option_c'):
                question.option_c = clean_mathematical_text(question.option_c)
            if hasattr(question, 'option_d'):
                question.option_d = clean_mathematical_text(question.option_d)

            if getattr(question, 'explanation', None) is not None:
                question.explanation = clean_mathematical_text(question.explanation)

            # Save cleaned question (use update_fields for efficiency when possible)
            update_fields = ['question']
            for opt in ('option_a', 'option_b', 'option_c', 'option_d'):
                if hasattr(question, opt):
                    update_fields.append(opt)
            if getattr(question, 'explanation', None) is not None:
                update_fields.append('explanation')

            try:
                question.save(update_fields=update_fields)
            except Exception:
                # Fallback to full save if update_fields fails for some reason
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
    
    try:
        # R2: If last answer incorrect, recommend simpler questions from same sub-topic (highest priority)
        last_answer = recent_answers[0]
        if not last_answer.is_correct:
            logger.info(f"Applying R2: Last answer incorrect for student {student_id}")
            simpler_ids = _get_simpler_questions_same_topic(
                last_answer.question.topic_id, 
                exclude_ids=[last_answer.question_id]
            )
            if simpler_ids:
                return simpler_ids
        
        # Check for streaks (need at least 3 answers for R12/R13)
        if len(recent_answers) >= CONSECUTIVE_STREAK:
            recent_correct = [ans.is_correct for ans in recent_answers[:CONSECUTIVE_STREAK]]
            
            # R12: 3 consecutive correct answers (harder challenge)
            if all(recent_correct):
                logger.info(f"Applying R12: 3 consecutive correct for student {student_id}")
                harder_ids = _get_harder_challenge_questions(recent_answers[0].question.topic_id)
                if harder_ids:
                    return harder_ids
            
            # R13: 3 consecutive incorrect answers (confidence boost)
            if not any(recent_correct):
                logger.info(f"Applying R13: 3 consecutive incorrect for student {student_id}")
                boost_ids = _get_confidence_boost_questions()
                if boost_ids:
                    return boost_ids
        
        # R3: 2-3 consecutive correct in same sub-topic (harder questions from same topic)
        if len(recent_answers) >= 2:
            last_two = recent_answers[:2]
            if (all(ans.is_correct for ans in last_two) and 
                last_two[0].question.topic_id == last_two[1].question.topic_id):
                logger.info(f"Applying R3: Consecutive correct in same topic for student {student_id}")
                harder_same_topic_ids = _get_harder_questions_same_topic(last_two[0].question.topic_id)
                if harder_same_topic_ids:
                    return harder_same_topic_ids
        
        return None
        
    except Exception as e:
        logger.exception(f"Error in apply_streak_rules for student {student_id}: {e}")
        return None

def _get_simpler_questions_same_topic(topic_id: int, exclude_ids: List[int]) -> List[int]:
    """Get simpler questions from the same topic."""
    try:
        questions = Question.objects.filter(
            topic_id=topic_id,
            difficulty__icontains="easy"
        ).exclude(id__in=exclude_ids).values_list('id', flat=True)
        
        result = list(questions[:2])  # Return up to 2 simpler questions
        logger.debug(f"Found {len(result)} simpler questions for topic {topic_id}")
        return result
    except Exception as e:
        logger.exception(f"Error getting simpler questions for topic {topic_id}: {e}")
        return []

def _get_harder_questions_same_topic(topic_id: int) -> List[int]:
    """Get harder questions from the same topic."""
    try:
        questions = Question.objects.filter(
            topic_id=topic_id,
            difficulty__icontains="hard"
        ).values_list('id', flat=True)
        
        result = list(questions[:1])  # Return 1 harder question
        logger.debug(f"Found {len(result)} harder questions for topic {topic_id}")
        return result
    except Exception as e:
        logger.exception(f"Error getting harder questions for topic {topic_id}: {e}")
        return []

def _get_harder_challenge_questions(topic_id: int) -> List[int]:
    """Get challenging questions for R12."""
    try:
        questions = Question.objects.filter(
            topic_id=topic_id,
            difficulty__icontains="hard"
        ).values_list('id', flat=True)
        
        result = list(questions[:1])
        logger.debug(f"Found {len(result)} challenge questions for topic {topic_id}")
        return result
    except Exception as e:
        logger.exception(f"Error getting challenge questions for topic {topic_id}: {e}")
        return []

def _get_confidence_boost_questions() -> List[int]:
    """Get easy questions for confidence boost."""
    try:
        questions = Question.objects.filter(
            difficulty__icontains="easy"
        ).order_by('?').values_list('id', flat=True)
        
        result = list(questions[:1])
        logger.debug(f"Found {len(result)} confidence boost questions")
        return result
    except Exception as e:
        logger.exception(f"Error getting confidence boost questions: {e}")
        return []


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
    neet_settings = getattr(settings, "NEET_SETTINGS", {})
    use_engine = neet_settings.get("USE_RULE_ENGINE", True)
    
    if not use_engine:
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
"""
Deterministic Question Selection Engine

This module implements a conflict-free, deterministic 14-rule engine for intelligent 
question selection across different test types (topic-based and random tests).

Architecture:
- Two-layer decision approach: quota planning (session-level) + candidate sourcing (rule application)
- Hard constraints (never violated): R8 (exclusion), R14 (topic distribution)
- Soft constraints (preferences): R1-R7, R9-R13 applied with systematic fallbacks
- Deterministic resolution: composite scoring with fixed weights and tie-breaking

Rules:
- R1: Accuracy-based recommendations (<60% accuracy) [Priority: 80]
- R2: Immediate simpler questions after incorrect answers [Priority: 100 - highest]
- R3: Harder questions after consecutive correct answers [Priority: 75]
- R4: Time-based easier questions (>120s average) [Priority: 60]
- R5: Harder questions for fast but inaccurate answers [Priority: 60]
- R6: Difficulty distribution (30% Easy, 40% Moderate, 30% Hard) [soft baseline]
- R7: NEET subject distribution (Physics, Chemistry, Biology) [soft unless full-length]
- R8: Exclude questions seen within last 15 days [HARD constraint]
- R9: Include high-weightage topics [embedded in selection]
- R10: Skip similar easy questions after "too easy" feedback [placeholder]
- R11: Insert easier bridge questions after "too hard" feedback [placeholder]
- R12: Harder challenge after 3 consecutive correct [Priority: 70]
- R13: Easy confidence boost after 3 consecutive incorrect [Priority: 70]
- R14: Weak/strong topic allocation (70%/20%/10%) [HARD constraint]

Composite Scoring:
score = w_rule*rule_priority + w_recency*recency + w_weightage*weightage + 
        w_difficulty*difficulty_match + w_random*deterministic_tiebreak
"""

import logging
import random
import hashlib
from typing import List, Set, Dict, Any, Optional, Tuple, Union, NamedTuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q, Count, Avg, QuerySet, Max
from django.utils import timezone

from ..models import Question, TestAnswer, Topic, TestSession, StudentProfile
from ..views.utils import clean_mathematical_text

logger = logging.getLogger(__name__)


@dataclass
class StudentStats:
    """Cached student statistics for deterministic selection"""
    accuracy_per_topic: Dict[int, float]
    last_answer_per_topic: Dict[int, bool]  # True if last answer was incorrect
    consecutive_correct_count_per_topic: Dict[int, int]
    consecutive_incorrect_count_per_topic: Dict[int, int]
    avg_solve_time_per_topic: Dict[int, float]
    last_seen_questions: Dict[int, datetime]  # question_id -> last_attempt_timestamp


@dataclass
class QuotaAllocation:
    """Topic and difficulty quota allocation"""
    weak_topics: List[int]
    strong_topics: List[int]
    random_topics: List[int]
    quotas: Dict[str, Dict[str, Dict[str, int]]]  # topic_type -> topic_id -> difficulty -> count
    
    @property
    def weak_count(self) -> int:
        """Total questions allocated to weak topics"""
        return sum(
            sum(difficulty_counts.values()) 
            for difficulty_counts in self.quotas.get("weak", {}).values()
        )
    
    @property
    def strong_count(self) -> int:
        """Total questions allocated to strong topics"""
        return sum(
            sum(difficulty_counts.values()) 
            for difficulty_counts in self.quotas.get("strong", {}).values()
        )
    
    @property
    def random_count(self) -> int:
        """Total questions allocated to random topics"""
        return sum(
            sum(difficulty_counts.values()) 
            for difficulty_counts in self.quotas.get("random", {}).values()
        )


@dataclass
class CandidateQuestion:
    """Question candidate with metadata for scoring"""
    question_id: int
    topic_id: int
    difficulty: str
    highest_rule_priority: int
    weightage_score: float
    last_seen_timestamp: Optional[datetime]


# Configuration from settings
NEET_SETTINGS = getattr(settings, "NEET_SETTINGS", {})

# Engine configuration
USE_RULE_ENGINE = NEET_SETTINGS.get("USE_RULE_ENGINE", True)
EXCLUSION_DAYS = NEET_SETTINGS.get("EXCLUSION_DAYS", 15)

# High-weightage topics (configurable)
HIGH_WEIGHT_TOPICS = NEET_SETTINGS.get("HIGH_WEIGHT_TOPICS", [
    "Human Physiology", "Organic Chemistry", "Mechanics",
    "Coordination Compounds", "Thermodynamics", "Genetics"
])

# Subject mappings for NEET
NEET_SUBJECTS = {
    "Physics": ["Physics"],
    "Chemistry": ["Chemistry"], 
    "Biology": ["Botany", "Zoology"]
}

# Difficulty mappings
DIFFICULTY_LEVELS = ["Easy", "Moderate", "Hard"]
DIFFICULTY_DISTRIBUTION = {
    "Easy": NEET_SETTINGS.get("DIFFICULTY_EASY_RATIO", 30) / 100,
    "Moderate": NEET_SETTINGS.get("DIFFICULTY_MODERATE_RATIO", 40) / 100,
    "Hard": NEET_SETTINGS.get("DIFFICULTY_HARD_RATIO", 30) / 100
}

# Rule thresholds
ACCURACY_THRESHOLD = NEET_SETTINGS.get("ACCURACY_THRESHOLD", 60)
TIME_THRESHOLD_SLOW = NEET_SETTINGS.get("TIME_THRESHOLD_SLOW", 120)
TIME_THRESHOLD_FAST = NEET_SETTINGS.get("TIME_THRESHOLD_FAST", 60)
CONSECUTIVE_STREAK = NEET_SETTINGS.get("CONSECUTIVE_STREAK", 3)

# R14: Weak/strong allocation ratios
WEAK_STRONG_RATIOS = {
    "weak": NEET_SETTINGS.get("WEAK_TOPIC_RATIO", 70) / 100,
    "strong": NEET_SETTINGS.get("STRONG_TOPIC_RATIO", 20) / 100,
    "random": NEET_SETTINGS.get("RANDOM_TOPIC_RATIO", 10) / 100
}

# Rule priority mapping for composite scoring
RULE_PRIORITIES = {
    "R2": 100,  # Last wrong -> simpler (highest immediate corrective need)
    "R1": 80,   # Accuracy < 60%
    "R3": 75,   # 2-3 consecutive correct
    "R12": 70,  # 3 consecutive correct stretch
    "R13": 70,  # 3 consecutive incorrect
    "R4": 60,   # avg_time > 120s
    "R5": 60,   # fast but inaccurate
    "R14_weak": 50,  # handled as quota, mid priority within quota
    "R14_strong": 50,
    "R9": 40,   # Moderate performance topics (40-80% accuracy)
    "random_pool": 10
}

# Composite score weights (tunable, must sum to 1.0)
COMPOSITE_WEIGHTS = {
    "w_rule": 0.45,        # Rule priority importance
    "w_recency": 0.25,     # Question recency (older = higher score)
    "w_weightage": 0.20,   # Curricular importance
    "w_difficulty_match": 0.09,  # Difficulty matching quota
    "w_random": 0.01       # Deterministic tie-breaking
}


class DeterministicSelectionEngine:
    """
    Deterministic rule-based selection engine implementing the two-layer approach.
    
    Layer A: Quota planning (session-level hard constraints)
    Layer B: Candidate sourcing (rule application with deterministic ranking)
    """
    
    def __init__(self, student_id: Optional[str] = None, session_id: Optional[int] = None):
        """
        Initialize the deterministic selection engine.
        
        Args:
            student_id: Student ID for personalized selection
            session_id: Current test session ID for deterministic seeding
        """
        self.student_id = student_id
        self.session_id = session_id
        self.logger = logger
        
        # Deterministic seed for pseudo-random operations
        self.seed = self._generate_deterministic_seed()
        
        # Cached student statistics
        self.student_stats: Optional[StudentStats] = None
        
    def _generate_deterministic_seed(self) -> int:
        """Generate deterministic seed from student_id and session_id"""
        if self.student_id and self.session_id:
            seed_string = f"{self.student_id}_{self.session_id}"
            return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        return 42  # Default seed for anonymous sessions
        
    def generate_questions(self, 
                          selected_topics: List[int],
                          question_count: int,
                          test_type: str = "custom",
                          exclude_question_ids: Optional[Set[int]] = None,
                          difficulty_distribution: Optional[Dict[str, float]] = None) -> QuerySet:
        """
        Main entry point for deterministic question generation.
        
        Args:
            selected_topics: List of topic IDs (empty for random tests)
            question_count: Number of questions to generate
            test_type: Type of test ("custom", "random", "platform")
            exclude_question_ids: Questions to exclude
            difficulty_distribution: Override default difficulty distribution
            
        Returns:
            QuerySet of selected Question objects
        """
        self.logger.info(f"Starting deterministic selection: {question_count} questions, "
                        f"test_type={test_type}, topics={len(selected_topics)}")
        
        # Store original question count for quota calculations
        self.original_question_count = question_count
        
        try:
            # Step 0: Validate inputs
            if question_count <= 0:
                self.logger.warning("Invalid question count requested")
                return Question.objects.none()
                
            exclude_question_ids = exclude_question_ids or set()
            
            # Step 1: Precompute student statistics
            if self.student_id:
                self.student_stats = self._compute_student_statistics()
            
            # Step 2: Build R8 excluded questions set (hard constraint)
            excluded_questions = self._build_excluded_questions_set(exclude_question_ids)
            
            # Step 3: Determine topic universe for this test
            topic_universe = self._determine_topic_universe(selected_topics, test_type)
            
            # Step 4: Compute R14 hard quotas (topic distribution)
            quota_allocation = self._compute_topic_quotas(question_count, topic_universe)
            
            # Step 5: Convert topic quotas into subject + difficulty buckets
            difficulty_dist = difficulty_distribution or DIFFICULTY_DISTRIBUTION
            quota_allocation = self._apply_difficulty_distribution(quota_allocation, difficulty_dist)
            
            # Step 6: Build rule-based candidate buckets
            candidate_pools = self._build_candidate_pools(topic_universe, excluded_questions)
            
            # Step 7: Apply R8 exclusion to all candidate buckets
            candidate_pools = self._apply_exclusions(candidate_pools, excluded_questions)
            
            # Step 8: Select questions using deterministic ranking
            selected_question_ids = self._select_questions_deterministically(
                quota_allocation, candidate_pools, topic_universe
            )
            
            # Step 9: Apply fallback strategy if needed
            if len(selected_question_ids) < question_count:
                selected_question_ids = self._apply_fallback_strategy(
                    selected_question_ids, question_count, topic_universe, excluded_questions
                )
            
            # Step 10: Final validation and truncation to exact count
            if selected_question_ids:
                # CRITICAL FIX: Ensure exact question count is returned
                if len(selected_question_ids) > question_count:
                    self.logger.warning(f"Truncating selection from {len(selected_question_ids)} to {question_count} questions")
                    selected_question_ids = selected_question_ids[:question_count]
                
                questions = Question.objects.filter(id__in=selected_question_ids)
                questions = self._clean_questions(questions)
                
                # Final validation
                actual_count = questions.count()
                if actual_count != question_count:
                    self.logger.error(f"CRITICAL: Expected {question_count} questions, got {actual_count}")
                
                self.logger.info(f"Selection completed: {actual_count} questions selected")
                return questions
            else:
                self.logger.warning("No questions selected")
                return Question.objects.none()
                
        except Exception as e:
            self.logger.exception(f"Deterministic selection failed: {e}")
            return Question.objects.none()
    
    def _compute_student_statistics(self) -> StudentStats:
        """
        Step 1: Precompute student statistics for deterministic selection.
        
        Returns:
            StudentStats object with cached performance metrics
        """
        if not self.student_id:
            return StudentStats(
                accuracy_per_topic={},
                last_answer_per_topic={},
                consecutive_correct_count_per_topic={},
                consecutive_incorrect_count_per_topic={},
                avg_solve_time_per_topic={},
                last_seen_questions={}
            )
        
        try:
            # Get completed test answers for statistical analysis
            completed_answers = TestAnswer.objects.filter(
                session__student_id=self.student_id,
                session__is_completed=True,
                selected_answer__isnull=False
            ).select_related('question__topic').order_by('answered_at')
            
            # Group answers by topic for analysis
            by_topic = defaultdict(list)
            last_seen_questions = {}
            
            for answer in completed_answers:
                topic_id = answer.question.topic_id
                by_topic[topic_id].append(answer)
                
                # Track when each question was last seen
                last_seen_questions[answer.question_id] = answer.answered_at
            
            # Compute per-topic statistics
            accuracy_per_topic = {}
            last_answer_per_topic = {}
            consecutive_correct_count_per_topic = {}
            consecutive_incorrect_count_per_topic = {}
            avg_solve_time_per_topic = {}
            
            for topic_id, answers in by_topic.items():
                # Accuracy calculation
                correct_count = sum(1 for a in answers if a.is_correct)
                total_count = len(answers)
                accuracy_per_topic[topic_id] = (correct_count / total_count * 100) if total_count > 0 else 0
                
                # Last answer status (True if last was incorrect)
                if answers:
                    last_answer_per_topic[topic_id] = not answers[-1].is_correct
                
                # Consecutive streaks (from most recent backwards)
                if len(answers) >= 2:
                    # Count consecutive correct from end
                    consecutive_correct = 0
                    for answer in reversed(answers):
                        if answer.is_correct:
                            consecutive_correct += 1
                        else:
                            break
                    consecutive_correct_count_per_topic[topic_id] = consecutive_correct
                    
                    # Count consecutive incorrect from end
                    consecutive_incorrect = 0
                    for answer in reversed(answers):
                        if not answer.is_correct:
                            consecutive_incorrect += 1
                        else:
                            break
                    consecutive_incorrect_count_per_topic[topic_id] = consecutive_incorrect
                
                # Average solve time
                times = [a.time_taken for a in answers if a.time_taken is not None]
                avg_solve_time_per_topic[topic_id] = sum(times) / len(times) if times else 0
            
            return StudentStats(
                accuracy_per_topic=accuracy_per_topic,
                last_answer_per_topic=last_answer_per_topic,
                consecutive_correct_count_per_topic=consecutive_correct_count_per_topic,
                consecutive_incorrect_count_per_topic=consecutive_incorrect_count_per_topic,
                avg_solve_time_per_topic=avg_solve_time_per_topic,
                last_seen_questions=last_seen_questions
            )
            
        except Exception as e:
            self.logger.exception(f"Failed to compute student statistics: {e}")
            return StudentStats({}, {}, {}, {}, {}, {})
    
    def _build_excluded_questions_set(self, additional_exclusions: Set[int]) -> Set[int]:
        """
        Step 2: Build R8 excluded questions set (hard constraint).
        
        Args:
            additional_exclusions: Additional question IDs to exclude
            
        Returns:
            Set of question IDs that must be excluded
        """
        excluded_questions = set(additional_exclusions)
        
        if self.student_id:
            # R8: Exclude questions seen within last EXCLUSION_DAYS
            cutoff_date = timezone.now() - timedelta(days=EXCLUSION_DAYS)
            
            recent_question_ids = TestAnswer.objects.filter(
                session__student_id=self.student_id,
                answered_at__gte=cutoff_date,
                session__is_completed=True
            ).values_list('question_id', flat=True)
            
            excluded_questions.update(recent_question_ids)
            
        self.logger.info(f"R8 exclusion: {len(excluded_questions)} questions excluded")
        return excluded_questions
    
    def _determine_topic_universe(self, selected_topics: List[int], test_type: str) -> List[int]:
        """
        Step 3: Determine topic universe for this test.
        
        Args:
            selected_topics: User-selected topic IDs
            test_type: Type of test
            
        Returns:
            List of topic IDs that form the universe for selection
        """
        if test_type == "random" or not selected_topics:
            # Use all available topics for random tests
            all_topics = list(Topic.objects.values_list('id', flat=True))
            self.logger.info(f"Topic universe: {len(all_topics)} topics (random test)")
            return all_topics
        else:
            # Use selected topics for custom tests
            self.logger.info(f"Topic universe: {len(selected_topics)} topics (custom test)")
            return selected_topics
    
    def _compute_topic_quotas(self, question_count: int, topic_universe: List[int]) -> QuotaAllocation:
        """
        Step 4: Compute R14 hard quotas (topic distribution).
        
        Args:
            question_count: Total number of questions needed
            topic_universe: Available topics for selection
            
        Returns:
            QuotaAllocation with weak/strong/random topic assignments
        """
        # Calculate quota counts using R14 ratios
        weak_count = max(1, round(question_count * WEAK_STRONG_RATIOS["weak"]))
        strong_count = max(1, round(question_count * WEAK_STRONG_RATIOS["strong"]))
        random_count = question_count - weak_count - strong_count
        
        # Ensure random_count is non-negative
        if random_count < 0:
            random_count = 0
            # Redistribute the excess
            excess = weak_count + strong_count - question_count
            if excess > 0:
                if weak_count > strong_count:
                    weak_count -= excess
                else:
                    strong_count -= excess
        
        # Categorize topics by student performance (if available)
        if self.student_stats and self.student_stats.accuracy_per_topic:
            weak_topics, strong_topics = self._categorize_topics_by_performance(topic_universe)
        else:
            # For new students, distribute evenly
            random.seed(self.seed)
            shuffled_topics = list(topic_universe)
            random.shuffle(shuffled_topics)
            
            split_point = len(shuffled_topics) // 2
            weak_topics = shuffled_topics[:split_point]
            strong_topics = shuffled_topics[split_point:]
        
        # Select topics for each category dynamically based on how many questions
        # we plan to allocate to that category and how many topics are available.
        # Aim: at least one topic per question when possible, but never exceed
        # the number of available topics. This avoids forcing a tiny fixed
        # number of topics (e.g., 5) regardless of question_count.
        def pick_topics_for_category(category_topics: List[int], total_questions_in_category: int) -> List[int]:
            if not category_topics or total_questions_in_category <= 0:
                return []

            # We want to distribute questions across as many topics as makes sense
            # without exceeding the number of available topics. Each selected
            # topic should get at least one question where possible.
            max_topics_by_questions = total_questions_in_category  # at most one per question
            num_topics = min(len(category_topics), max(1, max_topics_by_questions))

            # Keep deterministic ordering already applied earlier (sorting)
            return category_topics[:num_topics]

        weak_topics = pick_topics_for_category(weak_topics, weak_count)
        strong_topics = pick_topics_for_category(strong_topics, strong_count)

        # Random topics are any remaining topics not used in weak/strong
        used_topics = set(weak_topics + strong_topics)
        random_topics = [t for t in topic_universe if t not in used_topics]
        
        self.logger.info(f"R14 quotas - Weak: {weak_count}, Strong: {strong_count}, Random: {random_count}")
        self.logger.info(f"Topic categories - Weak: {len(weak_topics)}, Strong: {len(strong_topics)}, Random: {len(random_topics)}")
        
        return QuotaAllocation(
            weak_topics=weak_topics,
            strong_topics=strong_topics,
            random_topics=random_topics,
            quotas={
                "weak": {str(t): {} for t in weak_topics},
                "strong": {str(t): {} for t in strong_topics},
                "random": {str(t): {} for t in random_topics}
            }
        )
    
    def _categorize_topics_by_performance(self, topic_universe: List[int]) -> Tuple[List[int], List[int]]:
        """
        Categorize topics as weak (<60% accuracy) or strong (>=60% accuracy).
        
        Args:
            topic_universe: Available topics to categorize
            
        Returns:
            Tuple of (weak_topics, strong_topics)
        """
        weak_topics = []
        strong_topics = []
        
        for topic_id in topic_universe:
            accuracy = self.student_stats.accuracy_per_topic.get(topic_id, 0)
            if accuracy < ACCURACY_THRESHOLD:
                weak_topics.append(topic_id)
            else:
                strong_topics.append(topic_id)
        
        # Sort by performance for deterministic selection
        weak_topics.sort(key=lambda t: self.student_stats.accuracy_per_topic.get(t, 0))
        strong_topics.sort(key=lambda t: self.student_stats.accuracy_per_topic.get(t, 100), reverse=True)
        
        return weak_topics, strong_topics
    
    def _apply_difficulty_distribution(self, quota_allocation: QuotaAllocation, 
                                     difficulty_dist: Dict[str, float],
                                     question_count: int = None) -> QuotaAllocation:
        """
        Step 5: Apply R6 difficulty distribution (30% Easy, 40% Moderate, 30% Hard) 
        to the topic quotas.
        
        Args:
            quota_allocation: Topic allocation from R14
            difficulty_dist: Difficulty distribution ratios (30/40/30)
            question_count: Total questions (optional, uses self.original_question_count if not provided)
            
        Returns:
            Updated QuotaAllocation with difficulty-level quotas
        """
        # Get the total question count - use parameter if provided, otherwise use instance attribute
        total_questions = question_count if question_count is not None else getattr(self, 'original_question_count', 20)
        
        # Get the original question counts from R14 computation
        weak_count = max(1, round(total_questions * WEAK_STRONG_RATIOS["weak"]))
        strong_count = max(1, round(total_questions * WEAK_STRONG_RATIOS["strong"])) 
        random_count = total_questions - weak_count - strong_count
        
        # Calculate global difficulty quotas for the entire test (R6 rule)
        global_difficulty_quotas = {}
        allocated_so_far = 0
        
        difficulty_items = list(difficulty_dist.items())
        for i, (difficulty, ratio) in enumerate(difficulty_items):
            if i == len(difficulty_items) - 1:  # Last difficulty gets remainder
                count = total_questions - allocated_so_far
            else:
                count = max(0, round(total_questions * ratio))
                allocated_so_far += count
            global_difficulty_quotas[difficulty] = count
        
        self.logger.info(f"R6 global difficulty quotas: {global_difficulty_quotas}")
        
        # Track how many questions we've allocated per difficulty across all categories
        difficulty_tracker = {difficulty: 0 for difficulty in global_difficulty_quotas}
        
        for category in ["weak", "strong", "random"]:
            topics = getattr(quota_allocation, f"{category}_topics")
            if not topics:
                continue
                
            # Get total questions for this category
            if category == "weak":
                total_questions_in_category = weak_count
            elif category == "strong":
                total_questions_in_category = strong_count
            else:
                total_questions_in_category = max(0, random_count)
            
            if total_questions_in_category <= 0 or len(topics) == 0:
                continue
                
            # Distribute questions among topics in this category
            questions_per_topic = max(1, total_questions_in_category // len(topics))
            remainder = total_questions_in_category % len(topics)
            
            for i, topic_id in enumerate(topics):
                topic_str = str(topic_id)
                quota_allocation.quotas[category][topic_str] = {}
                
                # Base allocation plus remainder distribution
                topic_total = questions_per_topic + (1 if i < remainder else 0)
                
                # Distribute difficulty levels for this topic while respecting global quotas
                topic_allocated = 0
                for difficulty in difficulty_items:
                    difficulty_name = difficulty[0]
                    
                    # Calculate how many of this difficulty we can still allocate globally
                    remaining_global = global_difficulty_quotas[difficulty_name] - difficulty_tracker[difficulty_name]
                    
                    # Calculate ideal allocation for this topic-difficulty combo
                    remaining_topic = topic_total - topic_allocated
                    
                    if remaining_global > 0 and remaining_topic > 0:
                        # Take minimum of what's needed for topic and what's available globally
                        count = min(remaining_topic, remaining_global, 
                                  max(1, round(topic_total * difficulty[1])))
                        
                        if count > 0:
                            quota_allocation.quotas[category][topic_str][difficulty_name] = count
                            difficulty_tracker[difficulty_name] += count
                            topic_allocated += count
                
                # If we haven't allocated all questions for this topic, distribute remainder
                if topic_allocated < topic_total:
                    remaining = topic_total - topic_allocated
                    # Add to the most available difficulty
                    for difficulty_name in global_difficulty_quotas:
                        available = global_difficulty_quotas[difficulty_name] - difficulty_tracker[difficulty_name]
                        if available >= remaining:
                            current_count = quota_allocation.quotas[category][topic_str].get(difficulty_name, 0)
                            quota_allocation.quotas[category][topic_str][difficulty_name] = current_count + remaining
                            difficulty_tracker[difficulty_name] += remaining
                            break
        
        self.logger.info(f"Final difficulty distribution: {difficulty_tracker}")
        return quota_allocation
    
    def _build_candidate_pools(self, topic_universe: List[int], 
                             excluded_questions: Set[int]) -> Dict[str, List[CandidateQuestion]]:
        """
        Step 6: Build rule-based candidate buckets.
        
        Args:
            topic_universe: Available topics for selection
            excluded_questions: Questions to exclude (will be applied later)
            
        Returns:
            Dictionary mapping rule names to candidate question lists
        """
        candidate_pools = {
            "R1": [],   # accuracy < 60%
            "R2": [],   # last answer incorrect
            "R3": [],   # 2-3 consecutive correct
            "R4": [],   # avg_time > 120s
            "R5": [],   # fast but inaccurate
            "R12": [],  # 3 consecutive correct
            "R13": [],  # 3 consecutive incorrect
            "random_pool": []
        }
        
        if not self.student_stats:
            # For anonymous users, use random pool only
            candidate_pools["random_pool"] = self._get_all_candidates(topic_universe)
            return candidate_pools
        
        # Build rule-based candidate pools
        for topic_id in topic_universe:
            topic_candidates = self._get_topic_candidates(topic_id)
            
            # R1: Topics with accuracy < 60% (easy/moderate questions)
            accuracy = self.student_stats.accuracy_per_topic.get(topic_id, 0)
            if accuracy < ACCURACY_THRESHOLD:
                easy_moderate = [c for c in topic_candidates 
                               if c.difficulty.lower() in ['easy', 'moderate']]
                for candidate in easy_moderate:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R1"])
                candidate_pools["R1"].extend(easy_moderate)
            
            # R2: Last answer incorrect (easy questions)
            if self.student_stats.last_answer_per_topic.get(topic_id, False):
                easy_questions = [c for c in topic_candidates if c.difficulty.lower() == 'easy']
                for candidate in easy_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R2"])
                candidate_pools["R2"].extend(easy_questions)
            
            # R3: 2-3 consecutive correct (hard questions)
            consecutive_correct = self.student_stats.consecutive_correct_count_per_topic.get(topic_id, 0)
            if 2 <= consecutive_correct < CONSECUTIVE_STREAK:
                hard_questions = [c for c in topic_candidates if c.difficulty.lower() == 'hard']
                for candidate in hard_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R3"])
                candidate_pools["R3"].extend(hard_questions)
            
            # R4: Average time > 120s (easy questions)
            avg_time = self.student_stats.avg_solve_time_per_topic.get(topic_id, 0)
            if avg_time > TIME_THRESHOLD_SLOW:
                easy_questions = [c for c in topic_candidates if c.difficulty.lower() == 'easy']
                for candidate in easy_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R4"])
                candidate_pools["R4"].extend(easy_questions)
            
            # R5: Fast but inaccurate (hard questions)
            if avg_time < TIME_THRESHOLD_FAST and accuracy < ACCURACY_THRESHOLD:
                hard_questions = [c for c in topic_candidates if c.difficulty.lower() == 'hard']
                for candidate in hard_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R5"])
                candidate_pools["R5"].extend(hard_questions)
            
            # R12: 3 consecutive correct (hard challenge)
            if consecutive_correct >= CONSECUTIVE_STREAK:
                hard_questions = [c for c in topic_candidates if c.difficulty.lower() == 'hard']
                for candidate in hard_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R12"])
                candidate_pools["R12"].extend(hard_questions)
            
            # R13: 3 consecutive incorrect (easy confidence boost)
            consecutive_incorrect = self.student_stats.consecutive_incorrect_count_per_topic.get(topic_id, 0)
            if consecutive_incorrect >= CONSECUTIVE_STREAK:
                easy_questions = [c for c in topic_candidates if c.difficulty.lower() == 'easy']
                for candidate in easy_questions:
                    candidate.highest_rule_priority = max(candidate.highest_rule_priority, RULE_PRIORITIES["R13"])
                candidate_pools["R13"].extend(easy_questions)
            
            # Add all candidates to random pool as fallback
            for candidate in topic_candidates:
                if candidate.highest_rule_priority == 0:  # Not assigned to any rule
                    candidate.highest_rule_priority = RULE_PRIORITIES["random_pool"]
            candidate_pools["random_pool"].extend(topic_candidates)
        
        # Log candidate pool sizes with topic information
        for rule, candidates in candidate_pools.items():
            if candidates:
                # Show first few candidates with their topic info
                sample_info = []
                for candidate in candidates[:3]:  # Show first 3 as sample
                    try:
                        topic = Topic.objects.get(id=candidate.topic_id)
                        sample_info.append(f"Q{candidate.question_id}(Topic:{topic.name})")
                    except Topic.DoesNotExist:
                        sample_info.append(f"Q{candidate.question_id}(Topic:Unknown)")
                
                sample_text = ", ".join(sample_info)
                if len(candidates) > 3:
                    sample_text += f"... +{len(candidates)-3} more"
                
                self.logger.info(f"Candidate pool {rule}: {len(candidates)} questions - {sample_text}")
            else:
                self.logger.info(f"Candidate pool {rule}: 0 questions")
        
        return candidate_pools
    
    def _get_topic_candidates(self, topic_id: int) -> List[CandidateQuestion]:
        """Get all candidate questions for a specific topic"""
        questions = Question.objects.filter(topic_id=topic_id).values(
            'id', 'topic_id', 'difficulty'
        )
        
        candidates = []
        for q in questions:
            # Calculate weightage score (higher for high-weight topics)
            topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
            weightage_score = 1.0
            if topic_name in HIGH_WEIGHT_TOPICS:
                weightage_score = 1.5
            
            # Get last seen timestamp
            last_seen = None
            if self.student_stats:
                last_seen = self.student_stats.last_seen_questions.get(q['id'])
            
            candidate = CandidateQuestion(
                question_id=q['id'],
                topic_id=q['topic_id'],
                difficulty=q['difficulty'] or 'Moderate',
                highest_rule_priority=0,  # Will be set by rule application
                weightage_score=weightage_score,
                last_seen_timestamp=last_seen
            )
            candidates.append(candidate)
        
        return candidates
    
    def _get_all_candidates(self, topic_universe: List[int]) -> List[CandidateQuestion]:
        """Get all candidates from topic universe for fallback"""
        all_candidates = []
        for topic_id in topic_universe:
            all_candidates.extend(self._get_topic_candidates(topic_id))
        return all_candidates
    
    def _apply_exclusions(self, candidate_pools: Dict[str, List[CandidateQuestion]], 
                         excluded_questions: Set[int]) -> Dict[str, List[CandidateQuestion]]:
        """
        Step 7: Apply R8 exclusion to all candidate buckets.
        
        Args:
            candidate_pools: Rule-based candidate pools
            excluded_questions: Question IDs to exclude
            
        Returns:
            Filtered candidate pools with exclusions applied
        """
        filtered_pools = {}
        
        for rule, candidates in candidate_pools.items():
            filtered_candidates = [
                c for c in candidates 
                if c.question_id not in excluded_questions
            ]
            filtered_pools[rule] = filtered_candidates
            
            excluded_count = len(candidates) - len(filtered_candidates)
            if excluded_count > 0:
                self.logger.info(f"R8 exclusion in {rule}: {excluded_count} questions removed")
        
        return filtered_pools
    
    def _select_questions_deterministically(self, quota_allocation: QuotaAllocation,
                                          candidate_pools: Dict[str, List[CandidateQuestion]],
                                          topic_universe: List[int]) -> List[int]:
        """
        Step 8: Select questions using new sequential rule-based logic.
        
        New Logic:
        1. Remove R1-R13 questions from random_pool to avoid duplication
        2. Select 1-2 questions from R2,R3,R4,R5,R12,R13 based on difficulty preference
        3. Apply R9 rule (2% of total questions)
        4. Fill remaining from R1 ensuring subject/difficulty distribution
        5. Validate weak/strong/random distribution
        
        Args:
            quota_allocation: Topic and difficulty quotas (for distribution targets)
            candidate_pools: Rule-based candidate pools
            topic_universe: Available topics
            
        Returns:
            List of selected question IDs
        """
        selected_question_ids = []
        used_question_ids = set()
        
        # Get target counts from quota allocation
        weak_count = len(quota_allocation.weak_topics)
        strong_count = len(quota_allocation.strong_topics)
        target_question_count = self.original_question_count
        
        # Track difficulty distribution across all phases
        global_difficulty_counts = {'Easy': 0, 'Moderate': 0, 'Hard': 0}
        global_subject_counts = {'physics': 0, 'chemistry': 0, 'botany': 0, 'zoology': 0}
        
        self.logger.info(f"Starting new selection logic for {target_question_count} questions")
        
        # STEP 1: Remove R1-R13 questions from random_pool to avoid duplication
        rule_pools = ['R1', 'R2', 'R3', 'R4', 'R5', 'R12', 'R13']
        rule_question_ids = set()
        for rule in rule_pools:
            if rule in candidate_pools:
                rule_question_ids.update(c.question_id for c in candidate_pools[rule])
        
        # Clean random pool
        if 'random_pool' in candidate_pools:
            original_random_count = len(candidate_pools['random_pool'])
            candidate_pools['random_pool'] = [
                c for c in candidate_pools['random_pool'] 
                if c.question_id not in rule_question_ids
            ]
            self.logger.info(f"Cleaned random pool: {original_random_count} -> {len(candidate_pools['random_pool'])} questions")
        
        # STEP 2: Select 1 question from topics that satisfy each rule condition
        rule_selection_config = {
            'R2': {'count': 1, 'preferred_difficulty': 'Easy'},    # Last answer incorrect
            'R3': {'count': 1, 'preferred_difficulty': 'Hard'},   # 2-3 consecutive correct
            'R4': {'count': 1, 'preferred_difficulty': 'Easy'},   # Slow performance
            'R5': {'count': 1, 'preferred_difficulty': 'Hard'},   # Fast but inaccurate
            'R12': {'count': 1, 'preferred_difficulty': 'Hard'},  # 3+ consecutive correct
            'R13': {'count': 1, 'preferred_difficulty': 'Easy'}   # 3+ consecutive incorrect
        }
        
        for rule, config in rule_selection_config.items():
            # First identify topics that satisfy this rule condition
            satisfying_topics = self._get_topics_satisfying_rule(rule, topic_universe)
            
            if satisfying_topics:
                # Get all available questions from satisfying topics
                rule_candidates = []
                for topic_id in satisfying_topics:
                    topic_questions = Question.objects.filter(
                        topic_id=topic_id
                    ).exclude(
                        id__in=used_question_ids
                    ).values('id', 'topic_id', 'difficulty')
                    
                    for q in topic_questions:
                        # Calculate weightage score
                        topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
                        weightage_score = 1.5 if topic_name in HIGH_WEIGHT_TOPICS else 1.0
                        
                        candidate = CandidateQuestion(
                            question_id=q['id'],
                            topic_id=q['topic_id'],
                            difficulty=q['difficulty'] or 'Moderate',
                            highest_rule_priority=RULE_PRIORITIES.get(rule, 50),
                            weightage_score=weightage_score,
                            last_seen_timestamp=self.student_stats.last_seen_questions.get(q['id']) if self.student_stats else None
                        )
                        rule_candidates.append(candidate)
                
                if rule_candidates:
                    # Prefer questions matching the rule's difficulty preference
                    preferred_candidates = [
                        c for c in rule_candidates 
                        if c.difficulty.lower() == config['preferred_difficulty'].lower()
                    ]
                    
                    # Fall back to any difficulty if no preferred available
                    selection_pool = preferred_candidates if preferred_candidates else rule_candidates
                    
                    # Score and select top candidates
                    scored = self._score_candidates(selection_pool, config['preferred_difficulty'])
                    selected_count = min(config['count'], len(scored))
                    
                    for i in range(selected_count):
                        question_id = scored[i][1]
                        selected_question_ids.append(question_id)
                        used_question_ids.add(question_id)
                        
                        # Track difficulty and subject for this question
                        self._update_global_counts(question_id, global_difficulty_counts, global_subject_counts)
                    
                    self.logger.info(f"Selected {selected_count} from {rule} from topics {satisfying_topics[:3]}{'...' if len(satisfying_topics)>3 else ''} (preferred: {config['preferred_difficulty']})")
            else:
                self.logger.info(f"No topics satisfy rule {rule}")
        
        # STEP 3: Apply R9 rule (2% of total questions)
        r9_count = max(1, round(target_question_count * 0.02))  # At least 1, typically 2% of total
        self.logger.info(f"Applying R9 rule: selecting {r9_count} questions")

        # R9: Prefer HIGH_WEIGHT_TOPICS (from settings) first — small pedagogical injection
        r9_candidates = []
        hw_topic_ids = []
        try:
            # Map configured high-weight topic names to IDs in the current universe
            hw_topic_ids = list(Topic.objects.filter(name__in=HIGH_WEIGHT_TOPICS, id__in=topic_universe).values_list('id', flat=True))
        except Exception:
            hw_topic_ids = []

        if hw_topic_ids:
            self.logger.info(f"R9: Using high-weight topics for R9 selection: {hw_topic_ids}")
            for topic_id in hw_topic_ids:
                topic_questions = Question.objects.filter(topic_id=topic_id).exclude(id__in=used_question_ids).values('id', 'topic_id', 'difficulty')
                for q in topic_questions:
                    candidate = CandidateQuestion(
                        question_id=q['id'],
                        topic_id=q['topic_id'],
                        difficulty=q['difficulty'] or 'Moderate',
                        highest_rule_priority=RULE_PRIORITIES.get("R9", 40),
                        weightage_score=1.5,  # high-weight topic
                        last_seen_timestamp=self.student_stats.last_seen_questions.get(q['id']) if self.student_stats else None
                    )
                    r9_candidates.append(candidate)

        # Fallback: if no high-weight topic candidates, use moderate-performance topics as before
        if not r9_candidates and self.student_stats:
            r9_satisfying_topics = [t for t in topic_universe if 40 <= self.student_stats.accuracy_per_topic.get(t, 50) <= 80]
            if r9_satisfying_topics:
                try:
                    r9_topic_names = list(Topic.objects.filter(id__in=r9_satisfying_topics[:5]).values_list('name', flat=True))
                    if len(r9_satisfying_topics) > 5:
                        r9_topic_names.append(f"... +{len(r9_satisfying_topics)-5} more")
                    self.logger.info(f"R9 fallback: Found {len(r9_satisfying_topics)} moderate-performance topics: {r9_topic_names}")
                except Exception:
                    self.logger.info(f"R9 fallback: Found {len(r9_satisfying_topics)} moderate-performance topics")

                for topic_id in r9_satisfying_topics:
                    topic_questions = Question.objects.filter(topic_id=topic_id).exclude(id__in=used_question_ids).values('id', 'topic_id', 'difficulty')
                    for q in topic_questions:
                        topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
                        weightage_score = 1.5 if topic_name in HIGH_WEIGHT_TOPICS else 1.0
                        candidate = CandidateQuestion(
                            question_id=q['id'],
                            topic_id=q['topic_id'],
                            difficulty=q['difficulty'] or 'Moderate',
                            highest_rule_priority=RULE_PRIORITIES.get("R9", 40),
                            weightage_score=weightage_score,
                            last_seen_timestamp=self.student_stats.last_seen_questions.get(q['id']) if self.student_stats else None
                        )
                        r9_candidates.append(candidate)

        if r9_candidates:
            scored_r9 = self._score_candidates(r9_candidates, 'Moderate')  # Prefer moderate difficulty
            r9_selected = min(r9_count, len(scored_r9))
            for i in range(r9_selected):
                question_id = scored_r9[i][1]
                selected_question_ids.append(question_id)
                used_question_ids.add(question_id)

                # Track difficulty and subject for this question
                self._update_global_counts(question_id, global_difficulty_counts, global_subject_counts)

            self.logger.info(f"Selected {r9_selected} questions using R9 rule (high-weight preference applied)")
        else:
            self.logger.info("R9: No candidates found for high-weight or moderate topics")
        
        # STEP 4: Fill remaining from topics with low accuracy (R1) with subject/difficulty distribution
        remaining_needed = target_question_count - len(selected_question_ids)
        if remaining_needed > 0:
            self.logger.info(f"Filling remaining {remaining_needed} questions from R1 topics (accuracy < {ACCURACY_THRESHOLD}%)")
            
            # Identify topics that satisfy R1 condition (accuracy < 60%)
            r1_satisfying_topics = []
            if self.student_stats:
                for topic_id in topic_universe:
                    accuracy = self.student_stats.accuracy_per_topic.get(topic_id, 0)
                    if accuracy < ACCURACY_THRESHOLD:
                        r1_satisfying_topics.append(topic_id)
            else:
                # For new students, use all topics as R1 candidates
                r1_satisfying_topics = topic_universe.copy()
            
            if r1_satisfying_topics:
                # Get topic names for logging
                try:
                    r1_topic_names = list(Topic.objects.filter(id__in=r1_satisfying_topics[:5]).values_list('name', flat=True))
                    if len(r1_satisfying_topics) > 5:
                        r1_topic_names.append(f"... +{len(r1_satisfying_topics)-5} more")
                    self.logger.info(f"R1: Found {len(r1_satisfying_topics)} topics with low accuracy: {r1_topic_names}")
                except Exception:
                    self.logger.info(f"R1: Found {len(r1_satisfying_topics)} topics with low accuracy")
                
                # Get all available questions from R1 satisfying topics
                r1_candidates = []
                for topic_id in r1_satisfying_topics:
                    topic_questions = Question.objects.filter(
                        topic_id=topic_id
                    ).exclude(
                        id__in=used_question_ids
                    ).values('id', 'topic_id', 'difficulty')
                    
                    for q in topic_questions:
                        topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
                        weightage_score = 1.5 if topic_name in HIGH_WEIGHT_TOPICS else 1.0
                        
                        candidate = CandidateQuestion(
                            question_id=q['id'],
                            topic_id=q['topic_id'],
                            difficulty=q['difficulty'] or 'Moderate',
                            highest_rule_priority=RULE_PRIORITIES.get("R1", 80),
                            weightage_score=weightage_score,
                            last_seen_timestamp=self.student_stats.last_seen_questions.get(q['id']) if self.student_stats else None
                        )
                        r1_candidates.append(candidate)
                
                if r1_candidates:
                    # Ensure subject and difficulty distribution
                    selected_r1 = self._select_with_distribution_constraints(
                        r1_candidates, remaining_needed, quota_allocation, global_difficulty_counts, global_subject_counts, used_question_ids
                    )
                    selected_question_ids.extend(selected_r1)
                    used_question_ids.update(selected_r1)
                    
                    # Update global counts for R1 selections
                    for question_id in selected_r1:
                        self._update_global_counts(question_id, global_difficulty_counts, global_subject_counts)
                        
                    self.logger.info(f"Selected {len(selected_r1)} questions from R1 topics with distribution constraints")
                else:
                    self.logger.warning("R1: No questions available from topics with low accuracy")
            else:
                self.logger.warning("R1: No topics found with low accuracy")
        
        self.logger.info(f"Sequential selection completed: {len(selected_question_ids)} questions")
        
        # Log final global distribution
        self.logger.info(f"Global difficulty distribution: {global_difficulty_counts}")
        self.logger.info(f"Global subject distribution: {global_subject_counts}")
        
        return selected_question_ids
    
    def _update_global_counts(self, question_id: int, difficulty_counts: dict, subject_counts: dict):
        """Update global difficulty and subject counts for a selected question."""
        try:
            question = Question.objects.get(id=question_id)
            
            # Update difficulty count
            difficulty = self._normalize_difficulty(question.difficulty)
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            
            # Update subject count  
            if question.topic:
                subject = question.topic.subject.lower() if question.topic.subject else 'unknown'
                # Keep all 6 NEET subjects separate
                if subject in ['physics', 'chemistry', 'botany', 'zoology', 'biology', 'math']:
                    subject_counts[subject] = subject_counts.get(subject, 0) + 1
                else:
                    # Handle any unknown subjects
                    subject_counts['unknown'] = subject_counts.get('unknown', 0) + 1
                
        except Question.DoesNotExist:
            pass
    
    def _get_candidates_for_topic_difficulty(self, candidate_pools: Dict[str, List[CandidateQuestion]],
                                           topic_id: int, difficulty: str, 
                                           used_question_ids: Set[int]) -> List[CandidateQuestion]:
        """Get candidates matching specific topic and difficulty requirements"""
        candidates = []
        
        # Gather candidates from all rule pools for this topic/difficulty
        for rule, pool in candidate_pools.items():
            for candidate in pool:
                if (candidate.topic_id == topic_id and 
                    candidate.difficulty.lower() == difficulty.lower() and
                    candidate.question_id not in used_question_ids):
                    candidates.append(candidate)
        
        # Remove duplicates while preserving highest rule priority
        unique_candidates = {}
        for candidate in candidates:
            q_id = candidate.question_id
            if q_id not in unique_candidates or candidate.highest_rule_priority > unique_candidates[q_id].highest_rule_priority:
                unique_candidates[q_id] = candidate
        
        return list(unique_candidates.values())
    
    def _select_with_distribution_constraints(self, candidates: List[CandidateQuestion], 
                                           needed_count: int, quota_allocation: QuotaAllocation,
                                           current_difficulty_counts: dict, current_subject_counts: dict,
                                           used_question_ids: Set[int]) -> List[int]:
        """
        Select questions from candidates while ensuring subject and difficulty distribution.
        
        Args:
            candidates: Available candidate questions
            needed_count: Number of questions to select
            quota_allocation: For accessing weak/strong topic distribution
            
        Returns:
            List of selected question IDs
        """
        if not candidates or needed_count <= 0:
            return []
        
        selected_ids = []
        
        # Calculate how many questions we still need to reach global R6 targets
        total_questions = self.original_question_count
        
        # Global R6 targets for full test
        global_easy_target = round(total_questions * 0.30)
        global_moderate_target = round(total_questions * 0.40) 
        global_hard_target = total_questions - global_easy_target - global_moderate_target
        
        # Calculate remaining targets based on what we've already selected
        remaining_easy_target = max(0, global_easy_target - current_difficulty_counts.get('Easy', 0))
        remaining_moderate_target = max(0, global_moderate_target - current_difficulty_counts.get('Moderate', 0))
        remaining_hard_target = max(0, global_hard_target - current_difficulty_counts.get('Hard', 0))
        
        # Adjust targets to fit needed_count
        total_remaining_target = remaining_easy_target + remaining_moderate_target + remaining_hard_target
        if total_remaining_target > needed_count:
            # Scale down proportionally
            scale = needed_count / total_remaining_target
            remaining_easy_target = round(remaining_easy_target * scale)
            remaining_moderate_target = round(remaining_moderate_target * scale)
            remaining_hard_target = needed_count - remaining_easy_target - remaining_moderate_target
        elif total_remaining_target < needed_count:
            # Need more questions - prioritize moderate
            deficit = needed_count - total_remaining_target
            remaining_moderate_target += deficit
        
        self.logger.info(f"Adjusted R1 targets: Easy={remaining_easy_target}, Moderate={remaining_moderate_target}, Hard={remaining_hard_target}")
        
        # Track counts (start with current global counts)
        difficulty_counts = {'Easy': 0, 'Moderate': 0, 'Hard': 0}
        subject_counts = dict(current_subject_counts)  # Copy current subject distribution
        
        # Group candidates by difficulty and subject
        candidates_by_difficulty = {'Easy': [], 'Moderate': [], 'Hard': []}
        candidates_by_subject = {'physics': [], 'chemistry': [], 'botany': [], 'zoology': []}
        
        for candidate in candidates:
            # Normalize difficulty
            diff = self._normalize_difficulty(candidate.difficulty)
            candidates_by_difficulty[diff].append(candidate)
            
            # Get subject from topic
            try:
                topic = Topic.objects.get(id=candidate.topic_id)
                subject = topic.subject.lower() if topic.subject else 'unknown'
                # Keep all 6 NEET subjects separate
                if subject in ['physics', 'chemistry', 'botany', 'zoology', 'biology', 'math']:
                    if subject not in candidates_by_subject:
                        candidates_by_subject[subject] = []
                    candidates_by_subject[subject].append(candidate)
            except Topic.DoesNotExist:
                pass
        
        # Remove empty subject lists
        candidates_by_subject = {k: v for k, v in candidates_by_subject.items() if v}
        
        # Phase 1: Fill difficulty targets in priority order (Moderate first, then Easy, then Hard)
        priority_order = [
            ('Moderate', remaining_moderate_target),
            ('Easy', remaining_easy_target),
            ('Hard', remaining_hard_target)
        ]
        
        for difficulty, target in priority_order:
            if target <= 0:
                continue
                
            available = candidates_by_difficulty[difficulty]
            if not available:
                self.logger.warning(f"No {difficulty} questions available for R1 selection")
                continue
                
            # Score and select candidates ensuring subject diversity
            scored = self._score_candidates(available, difficulty)
            selected_for_diff = 0
            
            # Calculate target per subject for this difficulty
            num_subjects = len(candidates_by_subject)
            target_per_subject = max(1, target // num_subjects) if num_subjects > 0 else target
            
            for score, question_id in scored:
                if selected_for_diff >= target or len(selected_ids) >= needed_count:
                    break
                
                # Find candidate and check subject balance
                candidate = next((c for c in available if c.question_id == question_id), None)
                if not candidate:
                    continue
                    
                try:
                    topic = Topic.objects.get(id=candidate.topic_id)
                    subject = topic.subject.lower() if topic.subject else 'unknown'
                    
                    # Keep all 6 NEET subjects separate
                    if subject in ['physics', 'chemistry', 'botany', 'zoology', 'biology', 'math']:
                        # Check subject balance - prefer underrepresented subjects
                        current_subject_count = subject_counts.get(subject, 0)
                        # Use per-difficulty per-subject target (derived from difficulty target)
                        max_per_subject = target_per_subject

                        if current_subject_count < max_per_subject:
                            selected_ids.append(question_id)
                            difficulty_counts[difficulty] += 1
                            subject_counts[subject] = current_subject_count + 1
                            selected_for_diff += 1
                        
                except Topic.DoesNotExist:
                    # If topic doesn't exist, still select to meet difficulty target
                    selected_ids.append(question_id)
                    difficulty_counts[difficulty] += 1
                    selected_for_diff += 1
            
            self.logger.info(f"Selected {selected_for_diff}/{target} {difficulty} questions from R1")
            # If we couldn't meet the difficulty target due to subject caps, relax caps and fill remaining
            if selected_for_diff < target and len(selected_ids) < needed_count:
                still_needed = min(target - selected_for_diff, needed_count - len(selected_ids))
                self.logger.info(f"Difficulty {difficulty}: subject-aware pass selected {selected_for_diff}, relaxing subject caps to fill {still_needed} more")
                for score, question_id in scored:
                    if still_needed <= 0 or len(selected_ids) >= needed_count:
                        break
                    if question_id in selected_ids:
                        continue
                    candidate = next((c for c in available if c.question_id == question_id), None)
                    if not candidate:
                        continue
                    # Select without subject cap now
                    selected_ids.append(question_id)
                    diff_label = self._normalize_difficulty(candidate.difficulty)
                    difficulty_counts[diff_label] = difficulty_counts.get(diff_label, 0) + 1
                    # Update subject counts where available
                    try:
                        topic = Topic.objects.get(id=candidate.topic_id)
                        subject = topic.subject.lower() if topic.subject else 'unknown'
                        if subject in ['physics', 'chemistry', 'botany', 'zoology', 'biology', 'math']:
                            subject_counts[subject] = subject_counts.get(subject, 0) + 1
                    except Topic.DoesNotExist:
                        pass
                    still_needed -= 1
                self.logger.info(f"After relaxing caps, added {min(target, selected_for_diff + (target - selected_for_diff)) - selected_for_diff} questions for {difficulty}")
        
        # Check if we met difficulty targets, if not try random pool for missing difficulties
        unmet_difficulties = []
        if difficulty_counts['Easy'] < remaining_easy_target:
            unmet_difficulties.append(('Easy', remaining_easy_target - difficulty_counts['Easy']))
        if difficulty_counts['Moderate'] < remaining_moderate_target:
            unmet_difficulties.append(('Moderate', remaining_moderate_target - difficulty_counts['Moderate']))
        if difficulty_counts['Hard'] < remaining_hard_target:
            unmet_difficulties.append(('Hard', remaining_hard_target - difficulty_counts['Hard']))
        
        # Phase 2: Fill any remaining slots with subject balance priority
        remaining = needed_count - len(selected_ids)
        if remaining > 0:
            unused_candidates = [c for c in candidates if c.question_id not in selected_ids]
            
            # If R1 pool doesn't have enough questions or missing difficulty targets, look into random pool
            if len(unused_candidates) < remaining or unmet_difficulties:
                missing_count = max(remaining - len(unused_candidates), 0)
                self.logger.info(f"R1 pool insufficient or missing difficulty targets. Need {missing_count} more candidates. Looking into random pool...")
                
                # Get additional candidates from random pool that are not already selected
                try:
                    # Get current topic universe
                    topic_universe = list(Topic.objects.values_list('id', flat=True))
                    
                    # Get questions from random pool that haven't been used
                    all_used_ids = set([c.question_id for c in candidates] + selected_ids + list(used_question_ids))
                    
                    additional_questions = Question.objects.filter(
                        topic_id__in=topic_universe
                    ).exclude(
                        id__in=all_used_ids
                    ).select_related('topic')
                    
                    # Prioritize questions with unmet difficulties
                    if unmet_difficulties:
                        # First try to get questions matching unmet difficulty targets
                        for diff, needed_count_for_diff in unmet_difficulties:
                            diff_questions = additional_questions.filter(
                                difficulty__iexact=diff
                            )[:needed_count_for_diff * 2]  # Get more than needed for selection
                            
                            for q in diff_questions:
                                try:
                                    topic_name = q.topic.name if q.topic else None
                                    weightage_score = 1.5 if topic_name in HIGH_WEIGHT_TOPICS else 1.0
                                    
                                    candidate = CandidateQuestion(
                                        question_id=q.id,
                                        topic_id=q.topic_id,
                                        difficulty=q.difficulty or 'Moderate',
                                        highest_rule_priority=RULE_PRIORITIES["random_pool"],
                                        weightage_score=weightage_score,
                                        last_seen_timestamp=None
                                    )
                                    unused_candidates.append(candidate)
                                except Exception:
                                    continue
                    
                    # If still need more, get any remaining questions
                    if len(unused_candidates) < remaining:
                        remaining_questions = additional_questions[:remaining * 2]
                        for q in remaining_questions:
                            if q.id not in [c.question_id for c in unused_candidates]:
                                try:
                                    topic_name = q.topic.name if q.topic else None
                                    weightage_score = 1.5 if topic_name in HIGH_WEIGHT_TOPICS else 1.0
                                    
                                    candidate = CandidateQuestion(
                                        question_id=q.id,
                                        topic_id=q.topic_id,
                                        difficulty=q.difficulty or 'Moderate',
                                        highest_rule_priority=RULE_PRIORITIES["random_pool"],
                                        weightage_score=weightage_score,
                                        last_seen_timestamp=None
                                    )
                                    unused_candidates.append(candidate)
                                except Exception:
                                    continue
                    
                    self.logger.info(f"Enhanced candidate pool with {len(unused_candidates)} total candidates from R1 + random pool")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get additional candidates from random pool: {e}")
            
            if unused_candidates:
                # Group unused by subject and select to balance subjects
                unused_by_subject = {}
                for candidate in unused_candidates:
                    try:
                        topic = Topic.objects.get(id=candidate.topic_id)
                        subject = topic.subject.lower() if topic.subject else 'unknown'
                        
                        # Keep all 6 NEET subjects separate
                        if subject in ['physics', 'chemistry', 'botany', 'zoology', 'biology', 'math']:
                            if subject not in unused_by_subject:
                                unused_by_subject[subject] = []
                            unused_by_subject[subject].append(candidate)
                    except Topic.DoesNotExist:
                        pass
                
                # Select remaining questions balancing subjects
                subjects = list(unused_by_subject.keys())
                subject_index = 0
                selected_remaining = 0
                
                while selected_remaining < remaining and any(unused_by_subject.values()):
                    if not subjects:
                        break
                        
                    current_subject = subjects[subject_index % len(subjects)]
                    
                    if unused_by_subject.get(current_subject):
                        # Score candidates from this subject
                        subject_candidates = unused_by_subject[current_subject]
                        scored = self._score_candidates(subject_candidates, 'Moderate')
                        
                        if scored:
                            question_id = scored[0][1]  # Take best scored
                            selected_ids.append(question_id)
                            
                            # Remove selected candidate from pool
                            unused_by_subject[current_subject] = [
                                c for c in unused_by_subject[current_subject] 
                                if c.question_id != question_id
                            ]
                            
                            # Update counters
                            selected_remaining += 1
                            subject_counts[current_subject] = subject_counts.get(current_subject, 0) + 1
                    
                    subject_index += 1
                    
                    # Prevent infinite loop
                    if subject_index > len(subjects) * remaining:
                        break
                
                self.logger.info(f"Phase 2: Selected {selected_remaining} additional questions for subject balance")
        
        # Final logging
        self.logger.info(f"Final R1 selection: Easy={difficulty_counts['Easy']}, "
                        f"Moderate={difficulty_counts['Moderate']}, Hard={difficulty_counts['Hard']}")
        self.logger.info(f"Final subject distribution: {subject_counts}")
        
        return selected_ids
    
    def _get_topics_satisfying_rule(self, rule: str, topic_universe: List[int]) -> List[int]:
        """
        Identify topics that satisfy the condition for a specific rule.
        
        Args:
            rule: Rule name (R2, R3, R4, R5, R12, R13)
            topic_universe: Available topics to check
            
        Returns:
            List of topic IDs that satisfy the rule condition
        """
        if not self.student_stats:
            return []
        
        satisfying_topics = []
        
        for topic_id in topic_universe:
            satisfies_rule = False
            
            if rule == "R2":
                # R2: Last answer incorrect for this topic
                satisfies_rule = self.student_stats.last_answer_per_topic.get(topic_id, False)
            
            elif rule == "R3":
                # R3: 2-3 consecutive correct in this topic
                consecutive_correct = self.student_stats.consecutive_correct_count_per_topic.get(topic_id, 0)
                satisfies_rule = 2 <= consecutive_correct < CONSECUTIVE_STREAK
            
            elif rule == "R4":
                # R4: Average time > 120s for this topic
                avg_time = self.student_stats.avg_solve_time_per_topic.get(topic_id, 0)
                satisfies_rule = avg_time > TIME_THRESHOLD_SLOW
            
            elif rule == "R5":
                # R5: Fast but inaccurate for this topic
                avg_time = self.student_stats.avg_solve_time_per_topic.get(topic_id, 0)
                accuracy = self.student_stats.accuracy_per_topic.get(topic_id, 0)
                satisfies_rule = avg_time < TIME_THRESHOLD_FAST and accuracy < ACCURACY_THRESHOLD
            
            elif rule == "R12":
                # R12: 3+ consecutive correct in this topic
                consecutive_correct = self.student_stats.consecutive_correct_count_per_topic.get(topic_id, 0)
                satisfies_rule = consecutive_correct >= CONSECUTIVE_STREAK
            
            elif rule == "R13":
                # R13: 3+ consecutive incorrect in this topic
                consecutive_incorrect = self.student_stats.consecutive_incorrect_count_per_topic.get(topic_id, 0)
                satisfies_rule = consecutive_incorrect >= CONSECUTIVE_STREAK
            
            if satisfies_rule:
                satisfying_topics.append(topic_id)
        
        self.logger.info(f"Rule {rule}: Found {len(satisfying_topics)} satisfying topics: {satisfying_topics}")
        return satisfying_topics

    def _get_topics_satisfying_rule(self, rule_name: str, topic_universe: List[int]) -> List[int]:
        """
        Return topic IDs from topic_universe that satisfy the specific rule condition.
        
        Args:
            rule_name: Rule identifier ('R2', 'R3', 'R4', 'R5', 'R12', 'R13')
            topic_universe: List of available topic IDs
            
        Returns:
            List of topic IDs that satisfy the rule condition
        """
        if not self.student_stats:
            return []

        satisfying_topics = []
        
        for topic_id in topic_universe:
            accuracy = self.student_stats.accuracy_per_topic.get(topic_id, 0)
            last_wrong = self.student_stats.last_answer_per_topic.get(topic_id, False)
            consecutive_correct = self.student_stats.consecutive_correct_count_per_topic.get(topic_id, 0)
            consecutive_incorrect = self.student_stats.consecutive_incorrect_count_per_topic.get(topic_id, 0)
            avg_time = self.student_stats.avg_solve_time_per_topic.get(topic_id, 0)

            if rule_name == "R2":
                # Last answer incorrect for this topic
                if last_wrong:
                    satisfying_topics.append(topic_id)
            elif rule_name == "R3":
                # 2-3 consecutive correct for this topic
                if 2 <= consecutive_correct < CONSECUTIVE_STREAK:
                    satisfying_topics.append(topic_id)
            elif rule_name == "R12":
                # 3+ consecutive correct for this topic
                if consecutive_correct >= CONSECUTIVE_STREAK:
                    satisfying_topics.append(topic_id)
            elif rule_name == "R13":
                # 3+ consecutive incorrect for this topic
                if consecutive_incorrect >= CONSECUTIVE_STREAK:
                    satisfying_topics.append(topic_id)
            elif rule_name == "R4":
                # Average time > 120s for this topic
                if avg_time and avg_time > TIME_THRESHOLD_SLOW:
                    satisfying_topics.append(topic_id)
            elif rule_name == "R5":
                # Fast but inaccurate for this topic
                if avg_time and avg_time < TIME_THRESHOLD_FAST and accuracy < ACCURACY_THRESHOLD:
                    satisfying_topics.append(topic_id)

        # Sort for deterministic behavior
        satisfying_topics.sort()
        
        if satisfying_topics:
            # Log topic names for clarity
            try:
                topic_names = Topic.objects.filter(id__in=satisfying_topics[:5]).values_list('name', flat=True)
                sample_names = list(topic_names)
                if len(satisfying_topics) > 5:
                    sample_names.append(f"... +{len(satisfying_topics)-5} more")
                self.logger.info(f"{rule_name} satisfying topics: {sample_names}")
            except Exception:
                self.logger.info(f"{rule_name} satisfying topics: {len(satisfying_topics)} topics")
        else:
            self.logger.info(f"{rule_name} satisfying topics: none found")
            
        return satisfying_topics

    def _score_candidates(self, candidates: List[CandidateQuestion], 
                         target_difficulty: str) -> List[Tuple[float, int]]:
        """
        Score candidates using composite scoring formula and return sorted list.
        
        Args:
            candidates: List of candidate questions
            target_difficulty: Target difficulty for difficulty matching
            
        Returns:
            List of (score, question_id) tuples sorted by score (highest first)
        """
        scored_candidates = []
        current_time = timezone.now()
        
        for candidate in candidates:
            # Rule priority score (normalized to 0-1)
            rule_score = candidate.highest_rule_priority / 100.0
            
            # Recency score (older questions get higher score, normalized to 0-1)
            recency_score = 0.5  # Default for unseen questions
            if candidate.last_seen_timestamp:
                days_since_seen = (current_time - candidate.last_seen_timestamp).days
                recency_score = min(1.0, days_since_seen / 30.0)  # Normalize over 30 days
            
            # Weightage score (already 0-1.5, normalize to 0-1)
            weightage_score = min(1.0, candidate.weightage_score / 1.5)
            
            # Difficulty match score
            difficulty_match_score = 1.0 if candidate.difficulty.lower() == target_difficulty.lower() else 0.5
            
            # Deterministic pseudo-random tiebreaker
            random_seed = f"{candidate.question_id}_{self.session_id or 0}"
            random_hash = int(hashlib.md5(random_seed.encode()).hexdigest()[:8], 16)
            random_score = (random_hash % 1000) / 1000.0  # 0-1 range
            
            # Composite score calculation
            composite_score = (
                COMPOSITE_WEIGHTS["w_rule"] * rule_score +
                COMPOSITE_WEIGHTS["w_recency"] * recency_score +
                COMPOSITE_WEIGHTS["w_weightage"] * weightage_score +
                COMPOSITE_WEIGHTS["w_difficulty_match"] * difficulty_match_score +
                COMPOSITE_WEIGHTS["w_random"] * random_score
            )
            
            scored_candidates.append((composite_score, candidate.question_id))
        
        # Sort by score (highest first), then by question_id for deterministic tie-breaking
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))
        
        return scored_candidates
    
    def _apply_fallback_strategy(self, current_selection: List[int], target_count: int,
                               topic_universe: List[int], excluded_questions: Set[int]) -> List[int]:
        """
        Step 9: Apply conservative fallback strategy following legacy approach.
        
        Args:
            current_selection: Currently selected question IDs
            target_count: Target number of questions
            topic_universe: Available topics
            excluded_questions: Questions to exclude
            
        Returns:
            Updated list of selected question IDs
        """
        selected_ids = list(current_selection)
        used_question_ids = set(selected_ids)
        remaining_needed = target_count - len(selected_ids)
        
        if remaining_needed <= 0:
            return selected_ids[:target_count]  # Truncate if over target
        
        self.logger.info(f"Applying conservative fallback strategy: need {remaining_needed} more questions")
        
        # Legacy-style fallback: prioritize random pool with subject distribution
        if remaining_needed > 0:
            # Get clean random pool (already cleaned of rule duplicates)
            available_questions = Question.objects.filter(
                topic_id__in=topic_universe
            ).exclude(
                id__in=excluded_questions | used_question_ids
            ).select_related('topic')
            
            # Group by subject for balanced distribution
            questions_by_subject = defaultdict(list)
            for question in available_questions:
                subject = question.topic.subject if question.topic else 'Unknown'
                questions_by_subject[subject].append(question.id)
            
            # Distribute across subjects
            subjects = list(questions_by_subject.keys())
            if subjects:
                # Shuffle deterministically
                random.seed(self.seed)
                random.shuffle(subjects)
                
                # Round-robin selection across subjects
                selected_count = 0
                subject_index = 0
                
                while selected_count < remaining_needed and any(questions_by_subject.values()):
                    current_subject = subjects[subject_index % len(subjects)]
                    
                    if questions_by_subject[current_subject]:
                        question_id = questions_by_subject[current_subject].pop(0)
                        selected_ids.append(question_id)
                        used_question_ids.add(question_id)
                        selected_count += 1
                        self.logger.info(f"Fallback selected Q{question_id} from {current_subject}")
                    
                    subject_index += 1
                    
                    # Prevent infinite loop
                    if subject_index > len(subjects) * 10:
                        break
                
                self.logger.info(f"Fallback completed: added {selected_count} questions with subject distribution")
        
        return selected_ids[:target_count]  # Ensure exact count
    
    def _fallback_relax_difficulty(self, topic_universe: List[int], excluded_questions: Set[int],
                                  used_question_ids: Set[int], needed_count: int) -> List[int]:
        """Fallback 1: Relax difficulty constraints within same topics"""
        additional_ids = []
        
        # Try to find questions from the same topics but different difficulties
        if self.student_stats:
            weak_topics = [t for t in topic_universe 
                          if self.student_stats.accuracy_per_topic.get(t, 0) < ACCURACY_THRESHOLD]
            
            for topic_id in weak_topics[:3]:  # Limit to top 3 weak topics
                if len(additional_ids) >= needed_count:
                    break
                    
                available_questions = Question.objects.filter(
                    topic_id=topic_id
                ).exclude(
                    id__in=excluded_questions | used_question_ids
                ).values_list('id', flat=True)
                
                available_list = list(available_questions)
                if available_list:
                    # Take up to needed count
                    take_count = min(len(available_list), needed_count - len(additional_ids))
                    additional_ids.extend(available_list[:take_count])
        
        return additional_ids
    
    def _fallback_cross_topic_same_subject(self, topic_universe: List[int], excluded_questions: Set[int],
                                         used_question_ids: Set[int], needed_count: int) -> List[int]:
        """Fallback 2: Use other topics from same subjects with legacy subject distribution"""
        additional_ids = []
        
        # Follow legacy method: distribute across subjects evenly like in utils.py
        subjects = ["Physics", "Chemistry", "Botany", "Zoology"]
        questions_per_subject = max(1, needed_count // 4)  # At least 1 question per subject
        remaining_questions = needed_count % 4  # Distribute remaining questions
        
        # Group topics by subject
        topics_by_subject = defaultdict(list)
        topic_subjects = Topic.objects.filter(id__in=topic_universe).values('id', 'subject')
        
        for topic_data in topic_subjects:
            subject = topic_data['subject']
            topic_id = topic_data['id']
            topics_by_subject[subject].append(topic_id)
        
        # Select questions per subject following legacy distribution
        for i, subject in enumerate(subjects):
            if len(additional_ids) >= needed_count:
                break
                
            # Calculate questions for this subject (legacy pattern)
            subject_question_count = questions_per_subject
            if i < remaining_questions:  # Distribute remaining questions to first few subjects
                subject_question_count += 1
            
            subject_topics = topics_by_subject.get(subject, [])
            if not subject_topics:
                continue
                
            # Get questions from this subject, excluding already used ones
            subject_questions = Question.objects.filter(
                topic_id__in=subject_topics
            ).exclude(
                id__in=excluded_questions | used_question_ids | set(additional_ids)
            ).values_list('id', flat=True)
            
            available_list = list(subject_questions)
            if available_list:
                # Shuffle deterministically for this subject
                random.seed(self.seed + hash(subject))
                random.shuffle(available_list)
                
                take_count = min(len(available_list), subject_question_count)
                subject_selected = available_list[:take_count]
                additional_ids.extend(subject_selected)
                self.logger.info(f"Fallback: Selected {len(subject_selected)} questions from {subject}")
            else:
                self.logger.warning(f"Fallback: No questions available for {subject}")
        
        # If we still need more questions (due to subject limitations), get from any remaining questions
        if len(additional_ids) < needed_count:
            remaining_needed = needed_count - len(additional_ids)
            remaining_questions = Question.objects.filter(
                topic_id__in=topic_universe
            ).exclude(
                id__in=excluded_questions | used_question_ids | set(additional_ids)
            ).values_list('id', flat=True)
            
            available_list = list(remaining_questions)
            if available_list:
                random.seed(self.seed)
                random.shuffle(available_list)
                additional_selected = available_list[:remaining_needed]
                additional_ids.extend(additional_selected)
                self.logger.info(f"Fallback: Added {len(additional_selected)} additional questions from any subject")
        
        return additional_ids
    
    def _fallback_random_pool(self, topic_universe: List[int], excluded_questions: Set[int],
                            used_question_ids: Set[int], needed_count: int) -> List[int]:
        """Fallback 3: Use random questions from topic universe"""
        available_questions = Question.objects.filter(
            topic_id__in=topic_universe
        ).exclude(
            id__in=excluded_questions | used_question_ids
        ).values_list('id', flat=True)
        
        available_list = list(available_questions)
        if not available_list:
            return []
        
        # Shuffle deterministically
        random.seed(self.seed)
        random.shuffle(available_list)
        
        take_count = min(len(available_list), needed_count)
        return available_list[:take_count]
    
    def _fallback_emergency_any_topic(self, topic_universe: List[int], excluded_questions: Set[int],
                                    used_question_ids: Set[int], needed_count: int) -> List[int]:
        """Fallback 4: Emergency - any available questions (respecting R8 exclusion)"""
        available_questions = Question.objects.exclude(
            id__in=excluded_questions | used_question_ids
        ).values_list('id', flat=True)
        
        available_list = list(available_questions)
        if not available_list:
            self.logger.warning("Emergency fallback: no questions available even without topic constraints")
            return []
        
        # Shuffle deterministically
        random.seed(self.seed)
        random.shuffle(available_list)
        
        take_count = min(len(available_list), needed_count)
        self.logger.warning(f"Emergency fallback: selected {take_count} questions from any topic")
        return available_list[:take_count]
    
    def _clean_questions(self, questions: QuerySet) -> QuerySet:
        """Clean mathematical text in questions (same as original implementation)"""
        questions_list = list(questions)
        for question in questions_list:
            try:
                # Clean question text and options
                question.question = clean_mathematical_text(question.question)
                if hasattr(question, 'option_a'):
                    question.option_a = clean_mathematical_text(question.option_a)
                if hasattr(question, 'option_b'):
                    question.option_b = clean_mathematical_text(question.option_b)
                if hasattr(question, 'option_c'):
                    question.option_c = clean_mathematical_text(question.option_c)
                if hasattr(question, 'option_d'):
                    question.option_d = clean_mathematical_text(question.option_d)
                if getattr(question, 'explanation', None):
                    question.explanation = clean_mathematical_text(question.explanation)
                
                # Save cleaned question
                update_fields = ['question']
                for opt in ('option_a', 'option_b', 'option_c', 'option_d'):
                    if hasattr(question, opt):
                        update_fields.append(opt)
                if getattr(question, 'explanation', None):
                    update_fields.append('explanation')
                
                question.save(update_fields=update_fields)
            except Exception as e:
                self.logger.warning(f"Failed to clean question {question.id}: {e}")
        
        return questions
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """Normalize difficulty labels."""
        if not difficulty:
            return "Moderate"  # Default to moderate
        
        difficulty_lower = difficulty.lower()
        if "easy" in difficulty_lower:
            return "Easy"
        elif "moderate" in difficulty_lower or "medium" in difficulty_lower:
            return "Moderate"
        elif "hard" in difficulty_lower or "difficult" in difficulty_lower:
            return "Hard"
        else:
            return "Moderate"  # Default fallback


# Backward Compatibility and Public Interface

def generate_questions_with_rules(selected_topics: List[int],
                                question_count: int,
                                student_id: Optional[str] = None,
                                session_id: Optional[int] = None,
                                test_type: str = "custom",
                                exclude_question_ids: Optional[Set[int]] = None,
                                difficulty_distribution: Optional[Dict[str, float]] = None) -> QuerySet:
    """
    Public interface for deterministic rule-based question generation.
    
    Args:
        selected_topics: List of topic IDs (empty for random tests)
        question_count: Number of questions to generate
        student_id: Student ID for personalized selection
        session_id: Current test session ID for deterministic seeding
        test_type: Type of test ("custom", "random", "platform")
        exclude_question_ids: Questions to exclude
        difficulty_distribution: Override default difficulty distribution
        
    Returns:
        QuerySet of selected Question objects
    """
    neet_settings = getattr(settings, "NEET_SETTINGS", {})
    use_engine = neet_settings.get("USE_RULE_ENGINE", True)
    
    if not use_engine:
        logger.info("Rule engine disabled, falling back to legacy selection")
        return _legacy_random_selection(selected_topics, question_count, exclude_question_ids)
    
    engine = DeterministicSelectionEngine(student_id=student_id, session_id=session_id)
    return engine.generate_questions(
        selected_topics=selected_topics,
        question_count=question_count,
        test_type=test_type,
        exclude_question_ids=exclude_question_ids,
        difficulty_distribution=difficulty_distribution
    )


def _legacy_random_selection(selected_topics: List[int], question_count: int, 
                           exclude_question_ids: Optional[Set[int]] = None) -> QuerySet:
    """
    Legacy fallback for when rule engine is disabled.
    Simple random selection respecting topic constraints.
    """
    try:
        if selected_topics:
            questions = Question.objects.filter(topic_id__in=selected_topics)
        else:
            questions = Question.objects.all()
        
        if exclude_question_ids:
            questions = questions.exclude(id__in=exclude_question_ids)
        
        # Get available question IDs and shuffle
        available_ids = list(questions.values_list('id', flat=True))
        if not available_ids:
            return Question.objects.none()
        
        random.shuffle(available_ids)
        selected_count = min(len(available_ids), question_count)
        selected_ids = available_ids[:selected_count]
        
        return Question.objects.filter(id__in=selected_ids)
        
    except Exception as e:
        logger.exception(f"Legacy selection failed: {e}")
        return Question.objects.none()


# Analysis and Debug Functions

def analyze_student_performance(student_id: str) -> Dict[str, Any]:
    """
    Analyze student performance for debugging and insights.
    
    Args:
        student_id: Student ID to analyze
        
    Returns:
        Dictionary with performance analysis
    """
    try:
        engine = DeterministicSelectionEngine(student_id=student_id)
        stats = engine._compute_student_statistics()
        
        analysis = {
            "total_topics_attempted": len(stats.accuracy_per_topic),
            "weak_topics": [],
            "strong_topics": [],
            "recent_streaks": {},
            "timing_issues": []
        }
        
        # Categorize topics by performance
        for topic_id, accuracy in stats.accuracy_per_topic.items():
            topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
            topic_data = {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "accuracy": accuracy
            }
            
            if accuracy < ACCURACY_THRESHOLD:
                analysis["weak_topics"].append(topic_data)
            else:
                analysis["strong_topics"].append(topic_data)
        
        # Sort by accuracy
        analysis["weak_topics"].sort(key=lambda x: x["accuracy"])
        analysis["strong_topics"].sort(key=lambda x: x["accuracy"], reverse=True)
        
        # Analyze streaks
        for topic_id in stats.accuracy_per_topic.keys():
            consecutive_correct = stats.consecutive_correct_count_per_topic.get(topic_id, 0)
            consecutive_incorrect = stats.consecutive_incorrect_count_per_topic.get(topic_id, 0)
            
            if consecutive_correct >= 2 or consecutive_incorrect >= 2:
                topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
                analysis["recent_streaks"][topic_name] = {
                    "consecutive_correct": consecutive_correct,
                    "consecutive_incorrect": consecutive_incorrect
                }
        
        # Analyze timing issues
        for topic_id, avg_time in stats.avg_solve_time_per_topic.items():
            if avg_time > TIME_THRESHOLD_SLOW or avg_time < TIME_THRESHOLD_FAST:
                topic_name = Topic.objects.filter(id=topic_id).values_list('name', flat=True).first()
                analysis["timing_issues"].append({
                    "topic_name": topic_name,
                    "avg_time": avg_time,
                    "issue": "too_slow" if avg_time > TIME_THRESHOLD_SLOW else "too_fast"
                })
        
        return analysis
        
    except Exception as e:
        logger.exception(f"Performance analysis failed for student {student_id}: {e}")
        return {"error": str(e)}


def test_deterministic_selection(student_id: str, session_id: int, selected_topics: List[int], 
                               question_count: int, iterations: int = 3) -> Dict[str, Any]:
    """
    Test deterministic behavior by running selection multiple times.
    
    Args:
        student_id: Student ID for testing
        session_id: Session ID for testing
        selected_topics: Topics to test with
        question_count: Number of questions to generate
        iterations: Number of times to run selection
        
    Returns:
        Test results showing consistency
    """
    results = []
    
    for i in range(iterations):
        engine = DeterministicSelectionEngine(student_id=student_id, session_id=session_id)
        questions = engine.generate_questions(
            selected_topics=selected_topics,
            question_count=question_count,
            test_type="custom"
        )
        
        question_ids = list(questions.values_list('id', flat=True))
        results.append(question_ids)
    
    # Check consistency
    first_result = results[0]
    all_consistent = all(result == first_result for result in results[1:])
    
    return {
        "iterations": iterations,
        "consistent": all_consistent,
        "results": results,
        "question_count": len(first_result) if first_result else 0
    }
    
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
            
            # Use topic-wise analyzer instead of session-only last-question heuristics
            analysis = analyze_streak_rules(self.student_id, session_id=self.session_id)
            if not analysis:
                return []

            # Map analyzer keys to prioritized order
            priority = [
                'R2',  # last wrong -> simpler same-topic
                'R12', # three correct in topic -> challenge
                'R13', # three incorrect in topic -> confidence boost
                'R3'   # two correct in topic -> harder same-topic
            ]

            available_streak_ids = []
            for key in priority:
                ids = analysis.get(key) or []
                if not ids:
                    continue
                # Filter exclusions and ensure existence
                valid_ids = list(Question.objects.filter(id__in=ids).exclude(id__in=exclude_question_ids).values_list('id', flat=True))
                for vid in valid_ids:
                    if vid not in available_streak_ids:
                        available_streak_ids.append(vid)
                if available_streak_ids:
                    break

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


def _get_confidence_boost_questions_for_topic(topic_id: int) -> List[int]:
    """Get easy questions for confidence boost limited to a topic."""
    try:
        questions = Question.objects.filter(
            topic_id=topic_id,
            difficulty__icontains="easy"
        ).order_by('?').values_list('id', flat=True)

        result = list(questions[:1])
        logger.debug(f"Found {len(result)} confidence boost questions for topic {topic_id}")
        return result
    except Exception as e:
        logger.exception(f"Error getting confidence boost questions for topic {topic_id}: {e}")
        return []


# Backward Compatibility and Public Interface

# Backward compatibility alias
SelectionEngine = DeterministicSelectionEngine
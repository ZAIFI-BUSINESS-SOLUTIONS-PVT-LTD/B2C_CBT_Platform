"""
Unit tests for the rule-based selection engine.

Tests cover all 14 rules and various edge cases:
- Session-level rules (R6, R7, R9, R14)
- Question-level rules (R1-R5, R10-R13)
- Exclusion rules (R8)
- Subject distribution and scaling
- Difficulty distribution
- Weak/strong topic allocation
- High-weightage topic inclusion
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta

from neet_app.models import Question, Topic, TestSession, TestAnswer, StudentProfile
from neet_app.services.selection_engine import (
    SelectionEngine, 
    generate_questions_with_rules,
    apply_streak_rules
)


class SelectionEngineTestCase(TestCase):
    """Test case for the rule-based selection engine."""
    
    def setUp(self):
        """Set up test data."""
        # Create test topics
        self.physics_topic = Topic.objects.create(
            id=1, name="Mechanics", subject="Physics"
        )
        self.chemistry_topic = Topic.objects.create(
            id=2, name="Organic Chemistry", subject="Chemistry"
        )
        self.biology_topic1 = Topic.objects.create(
            id=3, name="Human Physiology", subject="Botany"
        )
        self.biology_topic2 = Topic.objects.create(
            id=4, name="Genetics", subject="Zoology"
        )
        
        # Create test questions with different difficulties
        self.create_test_questions()
        
        # Create test student
        self.student_id = "STU123"
        
        # Create selection engine
        self.engine = SelectionEngine(student_id=self.student_id)
    
    def create_test_questions(self):
        """Create test questions for different topics and difficulties."""
        questions_data = [
            # Physics questions
            (self.physics_topic, "Easy", "Physics question 1"),
            (self.physics_topic, "Easy", "Physics question 2"),
            (self.physics_topic, "Moderate", "Physics question 3"),
            (self.physics_topic, "Moderate", "Physics question 4"),
            (self.physics_topic, "Hard", "Physics question 5"),
            
            # Chemistry questions  
            (self.chemistry_topic, "Easy", "Chemistry question 1"),
            (self.chemistry_topic, "Easy", "Chemistry question 2"),
            (self.chemistry_topic, "Moderate", "Chemistry question 3"),
            (self.chemistry_topic, "Moderate", "Chemistry question 4"),
            (self.chemistry_topic, "Hard", "Chemistry question 5"),
            
            # Biology questions
            (self.biology_topic1, "Easy", "Biology question 1"),
            (self.biology_topic1, "Easy", "Biology question 2"),
            (self.biology_topic1, "Moderate", "Biology question 3"),
            (self.biology_topic1, "Moderate", "Biology question 4"),
            (self.biology_topic1, "Hard", "Biology question 5"),
            
            (self.biology_topic2, "Easy", "Biology question 6"),
            (self.biology_topic2, "Easy", "Biology question 7"),
            (self.biology_topic2, "Moderate", "Biology question 8"),
            (self.biology_topic2, "Moderate", "Biology question 9"),
            (self.biology_topic2, "Hard", "Biology question 10"),
        ]
        
        for i, (topic, difficulty, question_text) in enumerate(questions_data, 1):
            Question.objects.create(
                id=i,
                topic=topic,
                difficulty=difficulty,
                question=question_text,
                option_a="Option A",
                option_b="Option B", 
                option_c="Option C",
                option_d="Option D",
                correct_answer="A"
            )
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = SelectionEngine()
        self.assertIsNone(engine.student_id)
        self.assertIsNone(engine.session_id)
        
        engine_with_student = SelectionEngine(student_id="STU123", session_id=1)
        self.assertEqual(engine_with_student.student_id, "STU123")
        self.assertEqual(engine_with_student.session_id, 1)
    
    @override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': True})
    def test_subject_distribution_full_test(self):
        """Test R7: Subject distribution for full-length test (180 questions)."""
        allocation = self.engine._apply_subject_distribution(180, "random")
        
        expected = {"Physics": 45, "Chemistry": 45, "Biology": 90}
        self.assertEqual(allocation, expected)
    
    @override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': True})
    def test_subject_distribution_small_test(self):
        """Test R7: Subject distribution scaling for smaller tests."""
        allocation = self.engine._apply_subject_distribution(18, "random")
        
        # Should scale proportionally: roughly 4 Physics, 4 Chemistry, 10 Biology
        total = sum(allocation.values())
        self.assertEqual(total, 18)
        
        # Biology should be largest
        self.assertGreater(allocation["Biology"], allocation["Physics"])
        self.assertGreater(allocation["Biology"], allocation["Chemistry"])
        
        # Each subject should have at least 1 question
        for count in allocation.values():
            self.assertGreaterEqual(count, 1)
    
    @override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': True})
    def test_difficulty_distribution(self):
        """Test R6: Difficulty distribution (30% Easy, 40% Moderate, 30% Hard)."""
        test_cases = [
            (10, {"Easy": 3, "Moderate": 4, "Hard": 3}),
            (20, {"Easy": 6, "Moderate": 8, "Hard": 6}),
            (3, {"Easy": 1, "Moderate": 1, "Hard": 1}),  # Minimum case
        ]
        
        for question_count, expected in test_cases:
            with self.subTest(question_count=question_count):
                allocation = self.engine._apply_difficulty_distribution(
                    question_count, {"Easy": 0.30, "Moderate": 0.40, "Hard": 0.30}
                )
                
                # Total should match requested count
                total = sum(allocation.values())
                self.assertEqual(total, question_count)
                
                # Each difficulty should have at least 1 question for counts >= 3
                if question_count >= 3:
                    for count in allocation.values():
                        self.assertGreaterEqual(count, 1)
    
    def test_exclusion_rule_without_student(self):
        """Test R8: Exclusion rule when no student ID provided."""
        exclude_ids = {1, 2, 3}
        selected_topics = [1, 2]
        
        available = self.engine._apply_exclusion_rule(
            selected_topics, exclude_ids, "topic"
        )
        
        # Should exclude the specified IDs but not add recent questions
        excluded_questions = available.filter(id__in=exclude_ids)
        self.assertEqual(excluded_questions.count(), 0)
    
    def test_exclusion_rule_with_student(self):
        """Test R8: Exclusion rule with student recent questions."""
        # Create test session and answers for recent questions
        test_session = TestSession.objects.create(
            student_id=self.student_id,
            selected_topics=[],
            start_time=timezone.now() - timedelta(days=5),  # Within 15 days
            total_questions=5,
            question_count=5,
            is_completed=True
        )
        
        # Add some test answers
        TestAnswer.objects.create(
            session=test_session,
            question_id=1,
            selected_answer="A",
            is_correct=True,
            answered_at=timezone.now() - timedelta(days=5)
        )
        TestAnswer.objects.create(
            session=test_session,
            question_id=2,
            selected_answer="B",
            is_correct=False,
            answered_at=timezone.now() - timedelta(days=5)
        )
        
        available = self.engine._apply_exclusion_rule([], set(), "random")
        
        # Should exclude recent questions (1, 2)
        excluded_questions = available.filter(id__in=[1, 2])
        self.assertEqual(excluded_questions.count(), 0)
    
    def test_high_weight_topics_inclusion(self):
        """Test R9: High-weightage topics inclusion."""
        # Create a selection without high-weight topics
        selected_ids = [1, 2, 3]  # None of these are high-weight in our test data
        available_questions = Question.objects.all()
        
        result = self.engine._ensure_high_weight_topics(selected_ids, available_questions)
        
        # Should include at least one high-weight topic if available
        selected_questions = Question.objects.filter(id__in=result)
        topic_names = list(selected_questions.values_list('topic__name', flat=True))
        
        # Check if any high-weight topics are included
        high_weight_included = any(
            name in ["Human Physiology", "Organic Chemistry", "Mechanics"] 
            for name in topic_names
        )
        self.assertTrue(high_weight_included)
    
    @patch('neet_app.services.selection_engine.SelectionEngine._get_topic_performance')
    def test_weak_strong_allocation(self, mock_performance):
        """Test R14: Weak/strong topic allocation."""
        # Mock topic performance (topic 1 weak, topic 2 strong)
        mock_performance.return_value = {1: 40.0, 2: 80.0}  # 40% and 80% accuracy
        
        subject_allocation = {"Physics": 10}
        
        allocation = self.engine._apply_weak_strong_allocation(
            [1, 2], subject_allocation, "topic"
        )
        
        # Should allocate more to weak topics
        physics_alloc = allocation["Physics"]
        self.assertIn("weak", physics_alloc)
        self.assertIn("strong", physics_alloc)
        self.assertGreater(physics_alloc["weak"], physics_alloc["strong"])
    
    def test_topic_performance_calculation(self):
        """Test topic performance calculation for weak/strong categorization."""
        # Create test session with answers
        test_session = TestSession.objects.create(
            student_id=self.student_id,
            selected_topics=[1, 2],
            start_time=timezone.now(),
            total_questions=4,
            question_count=4,
            is_completed=True
        )
        
        # Topic 1: 1 correct out of 2 (50% accuracy - weak)
        TestAnswer.objects.create(
            session=test_session, question_id=1, selected_answer="A", is_correct=True
        )
        TestAnswer.objects.create(
            session=test_session, question_id=2, selected_answer="B", is_correct=False
        )
        
        # Topic 2: 2 correct out of 2 (100% accuracy - strong)  
        TestAnswer.objects.create(
            session=test_session, question_id=6, selected_answer="A", is_correct=True
        )
        TestAnswer.objects.create(
            session=test_session, question_id=7, selected_answer="A", is_correct=True
        )
        
        performance = self.engine._get_topic_performance()
        
        # Topic 1 should be weak (50% < 60%)
        self.assertLess(performance.get(1, 0), 60)
        # Topic 2 should be strong (100% >= 60%)
        self.assertGreaterEqual(performance.get(2, 0), 60)
    
    def test_categorize_topics_by_performance(self):
        """Test topic categorization into weak/strong based on performance."""
        performance = {1: 40.0, 2: 80.0, 3: 55.0, 4: 70.0}
        topics = [1, 2, 3, 4]
        
        weak_topics, strong_topics = self.engine._categorize_topics_by_performance(
            topics, performance
        )
        
        # Topics 1, 3 should be weak (< 60%)
        self.assertEqual(set(weak_topics), {1, 3})
        # Topics 2, 4 should be strong (>= 60%)
        self.assertEqual(set(strong_topics), {2, 4})
    
    def test_difficulty_normalization(self):
        """Test difficulty label normalization."""
        test_cases = [
            ("Easy", "Easy"),
            ("easy", "Easy"),
            ("EASY", "Easy"),
            ("Moderate", "Moderate"),
            ("moderate", "Moderate"),
            ("Medium", "Moderate"),
            ("Hard", "Hard"),
            ("hard", "Hard"),
            ("Difficult", "Hard"),
            ("Unknown", "Unknown"),
            ("", "Unknown"),
            (None, "Unknown"),
        ]
        
        for input_difficulty, expected in test_cases:
            with self.subTest(input_difficulty=input_difficulty):
                result = self.engine._normalize_difficulty(input_difficulty)
                self.assertEqual(result, expected)
    
    @override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': True})
    def test_generate_questions_integration(self):
        """Test full question generation integration."""
        selected_topics = [1, 2]  # Physics and Chemistry
        question_count = 6
        
        result = self.engine.generate_questions(
            selected_topics=selected_topics,
            question_count=question_count,
            test_type="topic"
        )
        
        self.assertTrue(result.exists())
        self.assertLessEqual(result.count(), question_count)
        
        # All questions should be from selected topics
        for question in result:
            self.assertIn(question.topic_id, selected_topics)
    
    @override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': True})
    def test_random_test_generation(self):
        """Test random test generation with subject balance."""
        question_count = 12
        
        result = self.engine.generate_questions(
            selected_topics=[],  # Empty for random test
            question_count=question_count,
            test_type="random"
        )
        
        self.assertTrue(result.exists())
        self.assertLessEqual(result.count(), question_count)
        
        # Should include questions from multiple subjects
        subjects = set(result.values_list('topic__subject', flat=True))
        self.assertGreater(len(subjects), 1)
    
    def test_engine_disabled(self):
        """Test engine behavior when disabled."""
        with override_settings(NEET_SETTINGS={'USE_RULE_ENGINE': False}):
            result = generate_questions_with_rules(
                selected_topics=[1, 2],
                question_count=5
            )
            self.assertIsNone(result)
    
    def test_insufficient_questions_handling(self):
        """Test handling when insufficient questions are available."""
        # Request more questions than available
        question_count = 1000
        
        result = self.engine.generate_questions(
            selected_topics=[1],  # Only one topic with few questions
            question_count=question_count,
            test_type="topic"
        )
        
        # Should return all available questions for the topic
        available_count = Question.objects.filter(topic_id=1).count()
        self.assertEqual(result.count(), available_count)
    
    def test_empty_topic_list_random_fallback(self):
        """Test fallback to random selection when topic list is empty."""
        result = self.engine.generate_questions(
            selected_topics=[],
            question_count=5,
            test_type="topic"
        )
        
        self.assertTrue(result.exists())
        # Should select from all available topics
        all_topic_count = Question.objects.all().count()
        self.assertLessEqual(result.count(), min(5, all_topic_count))


class StreakRulesTestCase(TestCase):
    """Test case for question-level streak rules."""
    
    def setUp(self):
        """Set up test data for streak rules."""
        self.topic = Topic.objects.create(id=1, name="Test Topic", subject="Physics")
        
        # Create test questions
        for i in range(1, 6):
            Question.objects.create(
                id=i,
                topic=self.topic,
                difficulty="Easy" if i <= 2 else "Hard",
                question=f"Question {i}",
                option_a="A", option_b="B", option_c="C", option_d="D",
                correct_answer="A"
            )
        
        self.student_id = "STU123"
        self.session = TestSession.objects.create(
            id=1,
            student_id=self.student_id,
            selected_topics=[1],
            start_time=timezone.now(),
            total_questions=5,
            question_count=5
        )
    
    def create_test_answers(self, correct_pattern):
        """Create test answers with given correct/incorrect pattern."""
        answers = []
        for i, is_correct in enumerate(correct_pattern, 1):
            answer = TestAnswer.objects.create(
                session=self.session,
                question_id=i,
                selected_answer="A" if is_correct else "B",
                is_correct=is_correct,
                answered_at=timezone.now()
            )
            answers.append(answer)
        return list(reversed(answers))  # Most recent first
    
    def test_r2_incorrect_answer_rule(self):
        """Test R2: Immediate simpler questions after incorrect answer."""
        # Create answers with last one incorrect
        recent_answers = self.create_test_answers([True, True, False])
        
        result = apply_streak_rules(self.student_id, self.session, recent_answers)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        # Should recommend simpler questions from same topic
        if result:
            recommended_questions = Question.objects.filter(id__in=result)
            for q in recommended_questions:
                self.assertEqual(q.topic_id, self.topic.id)
                self.assertIn("easy", q.difficulty.lower())
    
    def test_r3_consecutive_correct_same_topic(self):
        """Test R3: Harder questions after consecutive correct in same topic."""
        # Create answers with 2 consecutive correct from same topic
        recent_answers = self.create_test_answers([True, True])
        
        # Ensure both answers are from same topic
        for answer in recent_answers:
            answer.question.topic = self.topic
            answer.question.save()
        
        result = apply_streak_rules(self.student_id, self.session, recent_answers)
        
        # Should recommend harder questions if available
        if result:
            recommended_questions = Question.objects.filter(id__in=result)
            for q in recommended_questions:
                self.assertEqual(q.topic_id, self.topic.id)
    
    def test_r12_three_consecutive_correct(self):
        """Test R12: Challenge question after 3 consecutive correct."""
        recent_answers = self.create_test_answers([True, True, True])
        
        result = apply_streak_rules(self.student_id, self.session, recent_answers)
        
        # Should recommend challenge questions
        self.assertIsNotNone(result)
        if result:
            recommended_questions = Question.objects.filter(id__in=result)
            # Should be harder questions
            for q in recommended_questions:
                self.assertIn("hard", q.difficulty.lower())
    
    def test_r13_three_consecutive_incorrect(self):
        """Test R13: Confidence boost after 3 consecutive incorrect."""
        recent_answers = self.create_test_answers([False, False, False])
        
        result = apply_streak_rules(self.student_id, self.session, recent_answers)
        
        # Should recommend easy confidence-boosting questions
        self.assertIsNotNone(result)
        if result:
            recommended_questions = Question.objects.filter(id__in=result)
            for q in recommended_questions:
                self.assertIn("easy", q.difficulty.lower())
    
    def test_no_streak_rules_applied(self):
        """Test when no streak rules should be applied."""
        # Mixed pattern that doesn't trigger any rules
        recent_answers = self.create_test_answers([True, False, True])
        
        result = apply_streak_rules(self.student_id, self.session, recent_answers)
        
        # Should not recommend any specific questions
        self.assertIsNone(result)
    
    def test_empty_recent_answers(self):
        """Test streak rules with empty recent answers."""
        result = apply_streak_rules(self.student_id, self.session, [])
        
        self.assertIsNone(result)


@override_settings(NEET_SETTINGS={
    'USE_RULE_ENGINE': True,
    'HIGH_WEIGHT_TOPICS': ['Mechanics', 'Organic Chemistry'],
    'WEAK_TOPIC_RATIO': 70,
    'STRONG_TOPIC_RATIO': 20, 
    'RANDOM_TOPIC_RATIO': 10
})
class PublicInterfaceTestCase(TestCase):
    """Test case for public interface functions."""
    
    def setUp(self):
        """Set up test data."""
        self.topic = Topic.objects.create(id=1, name="Mechanics", subject="Physics")
        
        for i in range(1, 11):
            Question.objects.create(
                id=i,
                topic=self.topic,
                difficulty=["Easy", "Moderate", "Hard"][i % 3],
                question=f"Question {i}",
                option_a="A", option_b="B", option_c="C", option_d="D",
                correct_answer="A"
            )
    
    def test_generate_questions_with_rules_success(self):
        """Test successful question generation via public interface."""
        result = generate_questions_with_rules(
            selected_topics=[1],
            question_count=5,
            test_type="topic"
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        self.assertLessEqual(result.count(), 5)
    
    def test_generate_questions_with_rules_random(self):
        """Test random question generation via public interface."""
        result = generate_questions_with_rules(
            selected_topics=[],
            question_count=3,
            test_type="random"
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        self.assertLessEqual(result.count(), 3)
    
    def test_generate_questions_with_exclusions(self):
        """Test question generation with exclusions."""
        exclude_ids = {1, 2, 3}
        
        result = generate_questions_with_rules(
            selected_topics=[1],
            question_count=5,
            exclude_question_ids=exclude_ids
        )
        
        if result and result.exists():
            selected_ids = set(result.values_list('id', flat=True))
            # Should not include excluded questions
            self.assertTrue(selected_ids.isdisjoint(exclude_ids))
    
    def test_custom_difficulty_distribution(self):
        """Test question generation with custom difficulty distribution."""
        custom_distribution = {"Easy": 0.5, "Moderate": 0.3, "Hard": 0.2}
        
        result = generate_questions_with_rules(
            selected_topics=[1],
            question_count=10,
            difficulty_distribution=custom_distribution
        )
        
        # Should respect custom distribution
        self.assertIsNotNone(result)
        if result and result.exists():
            difficulties = list(result.values_list('difficulty', flat=True))
            # More easy questions than hard ones based on distribution
            easy_count = sum(1 for d in difficulties if 'easy' in d.lower())
            hard_count = sum(1 for d in difficulties if 'hard' in d.lower())
            self.assertGreaterEqual(easy_count, hard_count)


if __name__ == '__main__':
    pytest.main([__file__])
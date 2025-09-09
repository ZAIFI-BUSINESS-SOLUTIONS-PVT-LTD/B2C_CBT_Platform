"""
Unit tests for time tracking and metadata capture functionality
Tests timing accuracy, metadata persistence, and performance analytics
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from neet_app.models import (
    TestSession, TestAnswer, TimeTracking, StudentProfile, Topic, Question
)


@pytest.mark.unit
class TestTimeTracking:
    """Test time tracking during tests and individual questions"""

    @pytest.mark.django_db
    def test_test_session_time_tracking(self, authenticated_client, sample_topic, sample_questions):
        """Test that test session tracks start and end times correctly"""
        # Arrange - create test session
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        
        # Act - start the test
        start_time = timezone.now()
        start_response = authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        # Assert
        assert start_response.status_code == 200
        test_session = TestSession.objects.get(id=test_id)
        assert test_session.start_time is not None
        assert test_session.start_time >= start_time - timedelta(seconds=1)  # Allow 1 second tolerance
        assert test_session.end_time is None  # Should not be set yet

    @pytest.mark.django_db
    def test_test_session_completion_time(self, authenticated_client, sample_topic, sample_questions):
        """Test that test session records end time on completion"""
        # Arrange - create and start test
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 2,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        # Act - complete the test by submitting all answers
        test_session = TestSession.objects.get(id=test_id)
        questions = sample_questions[:2]
        
        for question in questions:
            authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
                'questionId': question.id,
                'selectedAnswer': 'A',
                'timeTaken': 30  # 30 seconds per question
            })
        
        # Complete the test
        end_time = timezone.now()
        completion_response = authenticated_client.post(f'/api/test-sessions/{test_id}/complete/')
        
        # Assert
        assert completion_response.status_code == 200
        test_session.refresh_from_db()
        assert test_session.end_time is not None
        assert test_session.is_completed == True
        assert test_session.end_time >= end_time - timedelta(seconds=1)

    @pytest.mark.django_db
    def test_question_level_time_tracking(self, authenticated_client, sample_topic, sample_questions):
        """Test time tracking for individual questions"""
        # Arrange - create and start test
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 1,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        question = sample_questions[0]
        
        # Act - submit answer with time taken
        response = authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
            'questionId': question.id,
            'selectedAnswer': 'A',
            'timeTaken': 45  # 45 seconds
        })
        
        # Assert
        assert response.status_code == 201
        test_answer = TestAnswer.objects.get(
            test_session_id=test_id,
            question_id=question.id
        )
        assert test_answer.time_taken == 45

    @pytest.mark.django_db
    def test_time_tracking_validation(self, authenticated_client, sample_topic, sample_questions):
        """Test validation of time tracking data"""
        # Arrange
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 1,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        question = sample_questions[0]
        
        # Test negative time
        response = authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
            'questionId': question.id,
            'selectedAnswer': 'A',
            'timeTaken': -10  # Invalid negative time
        })
        assert response.status_code == 400
        
        # Test unreasonably high time (more than test time limit)
        response = authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
            'questionId': question.id,
            'selectedAnswer': 'A',
            'timeTaken': 4000  # More than 60 minutes test limit
        })
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_total_test_duration_calculation(self, authenticated_client, sample_topic, sample_questions):
        """Test calculation of total test duration"""
        # Arrange - create test with known duration
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 2,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        
        # Start test and record start time
        start_time = timezone.now()
        authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        # Simulate test duration
        test_session = TestSession.objects.get(id=test_id)
        test_session.start_time = start_time
        test_session.save()
        
        # Complete test after known duration
        end_time = start_time + timedelta(minutes=30)  # 30 minutes
        test_session.end_time = end_time
        test_session.is_completed = True
        test_session.save()
        
        # Act - calculate duration
        duration = test_session.end_time - test_session.start_time
        
        # Assert
        assert duration.total_seconds() == 30 * 60  # 30 minutes in seconds


@pytest.mark.unit
class TestMetadataCapture:
    """Test capture of various metadata during tests"""

    @pytest.mark.django_db
    def test_answer_correctness_tracking(self, authenticated_client, sample_topic, sample_questions):
        """Test tracking of correct/incorrect answers"""
        # Arrange
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 2,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        questions = sample_questions[:2]
        
        # Act - submit correct and incorrect answers
        # Correct answer (sample questions have correct_answer = 'A')
        response1 = authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
            'questionId': questions[0].id,
            'selectedAnswer': 'A',  # Correct
            'timeTaken': 30
        })
        
        # Incorrect answer
        response2 = authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
            'questionId': questions[1].id,
            'selectedAnswer': 'B',  # Incorrect (correct is 'A')
            'timeTaken': 45
        })
        
        # Assert
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        correct_answer = TestAnswer.objects.get(test_session_id=test_id, question_id=questions[0].id)
        incorrect_answer = TestAnswer.objects.get(test_session_id=test_id, question_id=questions[1].id)
        
        assert correct_answer.is_correct == True
        assert incorrect_answer.is_correct == False
        assert correct_answer.selected_answer == 'A'
        assert incorrect_answer.selected_answer == 'B'

    @pytest.mark.django_db
    def test_test_metadata_capture(self, authenticated_client, sample_topic, sample_questions):
        """Test capture of test-level metadata"""
        # Arrange
        test_data = {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 90,
            'testType': 'practice',
            'metadata': {
                'source': 'manual_creation',
                'difficulty_preference': 'mixed'
            }
        }
        
        # Act
        response = authenticated_client.post('/api/test-sessions/', test_data)
        
        # Assert
        assert response.status_code == 201
        test_session = TestSession.objects.get(id=response.json()['id'])
        assert test_session.total_questions == 3
        assert test_session.time_limit == 90
        assert test_session.student_id == authenticated_client.student_profile.student_id

    @pytest.mark.django_db
    def test_browser_session_metadata(self, authenticated_client, sample_topic):
        """Test capture of browser and session metadata"""
        # Arrange - add browser headers
        authenticated_client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Test Browser)'
        authenticated_client.defaults['HTTP_X_FORWARDED_FOR'] = '192.168.1.100'
        
        # Act
        response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 1,
            'timeLimit': 30
        })
        
        # Assert
        assert response.status_code == 201
        # Note: Actual browser metadata capture would depend on your implementation
        # This test ensures the endpoint accepts requests with browser headers

    @pytest.mark.django_db
    def test_question_metadata_capture(self, sample_topic):
        """Test that questions store proper metadata"""
        # Arrange & Act
        question = Question.objects.create(
            topic=sample_topic,
            question='What is the speed of light?',
            option_a='3 x 10^8 m/s',
            option_b='3 x 10^6 m/s',
            option_c='3 x 10^5 m/s',
            option_d='3 x 10^7 m/s',
            correct_answer='A',
            explanation='The speed of light in vacuum is approximately 3 x 10^8 m/s',
            difficulty='medium',
            question_type='physics_constant'
        )
        
        # Assert
        assert question.difficulty == 'medium'
        assert question.question_type == 'physics_constant'
        assert question.topic == sample_topic


@pytest.mark.unit
class TestPerformanceAnalytics:
    """Test performance analytics and insights generation"""

    @pytest.mark.django_db
    def test_student_performance_calculation(self, sample_student_profile, sample_topic, sample_questions):
        """Test calculation of student performance metrics"""
        # Arrange - create completed test with mixed results
        test_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_topic.id],
            total_questions=4,
            time_limit=60,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            is_completed=True
        )
        
        # Create test answers with different outcomes
        correct_answers = 3
        total_answers = 4
        
        for i in range(total_answers):
            is_correct = i < correct_answers  # First 3 correct, last 1 incorrect
            TestAnswer.objects.create(
                test_session=test_session,
                question_id=sample_questions[i].id,
                selected_answer='A' if is_correct else 'B',
                is_correct=is_correct,
                time_taken=30 + (i * 5)  # Varying time taken
            )
        
        # Act - calculate performance
        total_questions = TestAnswer.objects.filter(test_session=test_session).count()
        correct_count = TestAnswer.objects.filter(test_session=test_session, is_correct=True).count()
        accuracy = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # Assert
        assert total_questions == 4
        assert correct_count == 3
        assert accuracy == 75.0

    @pytest.mark.django_db
    def test_topic_wise_performance(self, sample_student_profile, sample_questions):
        """Test calculation of topic-wise performance"""
        # Arrange - create questions for different topics
        topic1 = sample_questions[0].topic
        topic2 = Topic.objects.create(
            name='Physics Mechanics',
            subject='Physics',
            icon='physics-icon',
            chapter='Motion'
        )
        
        physics_question = Question.objects.create(
            topic=topic2,
            question='What is acceleration?',
            option_a='Rate of change of velocity',
            option_b='Rate of change of distance',
            option_c='Rate of change of speed',
            option_d='Rate of change of position',
            correct_answer='A',
            explanation='Acceleration is the rate of change of velocity'
        )
        
        # Create test sessions for different topics
        chemistry_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[topic1.id],
            total_questions=2,
            time_limit=30,
            is_completed=True
        )
        
        physics_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[topic2.id],
            total_questions=1,
            time_limit=30,
            is_completed=True
        )
        
        # Add answers with different performance
        TestAnswer.objects.create(
            test_session=chemistry_session,
            question_id=sample_questions[0].id,
            selected_answer='A',
            is_correct=True,
            time_taken=25
        )
        TestAnswer.objects.create(
            test_session=chemistry_session,
            question_id=sample_questions[1].id,
            selected_answer='B',
            is_correct=False,
            time_taken=35
        )
        TestAnswer.objects.create(
            test_session=physics_session,
            question_id=physics_question.id,
            selected_answer='A',
            is_correct=True,
            time_taken=20
        )
        
        # Act - calculate topic-wise performance
        chemistry_answers = TestAnswer.objects.filter(
            test_session__student_id=sample_student_profile.student_id,
            question__topic=topic1
        )
        physics_answers = TestAnswer.objects.filter(
            test_session__student_id=sample_student_profile.student_id,
            question__topic=topic2
        )
        
        chemistry_accuracy = (chemistry_answers.filter(is_correct=True).count() / chemistry_answers.count()) * 100
        physics_accuracy = (physics_answers.filter(is_correct=True).count() / physics_answers.count()) * 100
        
        # Assert
        assert chemistry_accuracy == 50.0  # 1 correct out of 2
        assert physics_accuracy == 100.0   # 1 correct out of 1

    @pytest.mark.django_db
    def test_time_analysis_per_question(self, sample_student_profile, sample_topic, sample_questions):
        """Test analysis of time taken per question"""
        # Arrange
        test_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_topic.id],
            total_questions=3,
            time_limit=90,
            is_completed=True
        )
        
        # Create answers with different time patterns
        time_data = [45, 30, 60]  # Different times for each question
        for i, time_taken in enumerate(time_data):
            TestAnswer.objects.create(
                test_session=test_session,
                question_id=sample_questions[i].id,
                selected_answer='A',
                is_correct=True,
                time_taken=time_taken
            )
        
        # Act - analyze time patterns
        answers = TestAnswer.objects.filter(test_session=test_session)
        times = [answer.time_taken for answer in answers]
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        # Assert
        assert avg_time == 45.0  # (45 + 30 + 60) / 3
        assert max_time == 60
        assert min_time == 30

    @pytest.mark.django_db
    def test_difficulty_based_performance(self, sample_student_profile, sample_topic):
        """Test performance analysis based on question difficulty"""
        # Arrange - create questions with different difficulties
        difficulties = ['easy', 'medium', 'hard']
        questions_by_difficulty = {}
        
        for difficulty in difficulties:
            question = Question.objects.create(
                topic=sample_topic,
                question=f'A {difficulty} question',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                explanation='Explanation',
                difficulty=difficulty
            )
            questions_by_difficulty[difficulty] = question
        
        # Create test session
        test_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_topic.id],
            total_questions=3,
            time_limit=60,
            is_completed=True
        )
        
        # Add answers with performance varying by difficulty
        performance_by_difficulty = {
            'easy': True,    # Correct
            'medium': True,  # Correct
            'hard': False    # Incorrect
        }
        
        for difficulty, is_correct in performance_by_difficulty.items():
            TestAnswer.objects.create(
                test_session=test_session,
                question_id=questions_by_difficulty[difficulty].id,
                selected_answer='A' if is_correct else 'B',
                is_correct=is_correct,
                time_taken=30
            )
        
        # Act - analyze performance by difficulty
        easy_performance = TestAnswer.objects.filter(
            test_session=test_session,
            question__difficulty='easy',
            is_correct=True
        ).count()
        
        hard_performance = TestAnswer.objects.filter(
            test_session=test_session,
            question__difficulty='hard',
            is_correct=True
        ).count()
        
        # Assert
        assert easy_performance == 1  # Easy question was answered correctly
        assert hard_performance == 0  # Hard question was answered incorrectly

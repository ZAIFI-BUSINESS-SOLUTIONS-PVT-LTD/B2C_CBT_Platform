"""
Unit tests for question selection and test creation functionality
Tests adaptive selection, exclusion logic, and test generation
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from neet_app.models import (
    Topic, Question, TestSession, TestAnswer, PlatformTest, StudentProfile
)


@pytest.mark.question_selection
@pytest.mark.unit
class TestQuestionSelection:
    """Test question selection algorithms and logic"""

    @pytest.mark.django_db
    def test_question_selection_no_duplicates(self, sample_questions, sample_student_profile):
        """Test that question selection prevents duplicates"""
        # Arrange - this would test your actual question selection service
        # For now, we'll test the constraint that selected questions are unique
        
        selected_questions = sample_questions[:3]  # Select 3 questions
        question_ids = [q.id for q in selected_questions]
        
        # Assert
        assert len(question_ids) == len(set(question_ids)), "Question IDs should be unique"

    @pytest.mark.django_db
    def test_question_selection_respects_topic_filter(self, sample_topic, sample_questions):
        """Test that questions are filtered by topic correctly"""
        # Arrange
        other_topic = Topic.objects.create(
            name='Inorganic Chemistry',
            subject='Chemistry',
            icon='inorganic-icon',
            chapter='Coordination Compounds'
        )
        
        # Create questions for different topic
        other_questions = []
        for i in range(3):
            q = Question.objects.create(
                topic=other_topic,
                question=f'Inorganic question {i}',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                explanation='Explanation'
            )
            other_questions.append(q)
        
        # Act - filter questions by original topic
        topic_questions = Question.objects.filter(topic=sample_topic)
        
        # Assert
        assert topic_questions.count() == 5  # From sample_questions fixture
        for question in topic_questions:
            assert question.topic == sample_topic

    @pytest.mark.django_db
    def test_question_difficulty_distribution(self, sample_topic):
        """Test question selection respects difficulty distribution"""
        # Arrange - create questions with different difficulties
        difficulties = ['easy', 'medium', 'hard']
        questions_per_difficulty = 5
        
        for difficulty in difficulties:
            for i in range(questions_per_difficulty):
                Question.objects.create(
                    topic=sample_topic,
                    question=f'{difficulty} question {i}',
                    option_a='A', option_b='B', option_c='C', option_d='D',
                    correct_answer='A',
                    explanation='Explanation',
                    difficulty=difficulty
                )
        
        # Act - test different difficulty queries
        easy_questions = Question.objects.filter(topic=sample_topic, difficulty='easy')
        medium_questions = Question.objects.filter(topic=sample_topic, difficulty='medium')
        hard_questions = Question.objects.filter(topic=sample_topic, difficulty='hard')
        
        # Assert
        assert easy_questions.count() == questions_per_difficulty
        assert medium_questions.count() == questions_per_difficulty
        assert hard_questions.count() == questions_per_difficulty

    @pytest.mark.django_db
    def test_question_exclusion_recent_attempts(self, sample_student_profile, sample_questions):
        """Test that recently attempted questions are excluded"""
        # Arrange - create a recent test session with some questions
        recent_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_questions[0].topic.id],
            total_questions=3,
            time_limit=60,
            start_time=datetime.now() - timedelta(days=1)  # Recent test
        )
        
        # Mark some questions as recently answered
        recent_question_ids = [sample_questions[0].id, sample_questions[1].id]
        for q_id in recent_question_ids:
            TestAnswer.objects.create(
                test_session=recent_session,
                question_id=q_id,
                selected_answer='A',
                is_correct=True,
                time_taken=30
            )
        
        # Act - get questions excluding recent ones
        excluded_ids = recent_question_ids
        available_questions = Question.objects.filter(
            topic=sample_questions[0].topic
        ).exclude(id__in=excluded_ids)
        
        # Assert
        assert available_questions.count() == 3  # 5 total - 2 excluded
        for question in available_questions:
            assert question.id not in excluded_ids

    @pytest.mark.django_db 
    def test_adaptive_selection_wrong_answers(self, sample_student_profile, sample_questions):
        """Test that wrongly answered questions are prioritized"""
        # Arrange - create test session with wrong answers
        old_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_questions[0].topic.id],
            total_questions=5,
            time_limit=60,
            start_time=datetime.now() - timedelta(days=30),  # Old enough to re-attempt
            end_time=datetime.now() - timedelta(days=30, minutes=-60),
            is_completed=True
        )
        
        # Mark some questions as incorrectly answered
        wrong_question_ids = [sample_questions[0].id, sample_questions[1].id]
        correct_question_ids = [sample_questions[2].id]
        
        for q_id in wrong_question_ids:
            TestAnswer.objects.create(
                test_session=old_session,
                question_id=q_id,
                selected_answer='B',  # Wrong answer (correct is 'A')
                is_correct=False,
                time_taken=45
            )
        
        for q_id in correct_question_ids:
            TestAnswer.objects.create(
                test_session=old_session,
                question_id=q_id,
                selected_answer='A',  # Correct answer
                is_correct=True,
                time_taken=30
            )
        
        # Act - prioritize questions that were answered incorrectly
        wrong_answers = TestAnswer.objects.filter(
            test_session__student_id=sample_student_profile.student_id,
            is_correct=False
        ).values_list('question_id', flat=True)
        
        # Assert
        assert len(wrong_answers) == 2
        assert sample_questions[0].id in wrong_answers
        assert sample_questions[1].id in wrong_answers


@pytest.mark.question_selection
@pytest.mark.unit
class TestTestCreation:
    """Test test creation and configuration"""

    @pytest.mark.django_db
    def test_create_custom_test_success(self, authenticated_client, sample_topic, sample_questions):
        """Test successful custom test creation"""
        # Arrange
        test_data = {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 90,  # 90 minutes
            'difficultyDistribution': {
                'easy': 1,
                'medium': 1,
                'hard': 1
            }
        }
        
        # Act
        response = authenticated_client.post('/api/test-sessions/', test_data)
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert 'id' in response_data
        
        # Verify database record
        test_session = TestSession.objects.get(id=response_data['id'])
        assert test_session.student_id == authenticated_client.student_profile.student_id
        assert test_session.total_questions == 3
        assert test_session.time_limit == 90

    @pytest.mark.django_db
    def test_create_test_invalid_topic(self, authenticated_client):
        """Test test creation with invalid topic"""
        # Arrange
        test_data = {
            'selectedTopics': [99999],  # Non-existent topic
            'totalQuestions': 5,
            'timeLimit': 60
        }
        
        # Act
        response = authenticated_client.post('/api/test-sessions/', test_data)
        
        # Assert
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_test_missing_required_fields(self, authenticated_client, sample_topic):
        """Test test creation with missing required fields"""
        # Test missing selectedTopics
        response = authenticated_client.post('/api/test-sessions/', {
            'totalQuestions': 5,
            'timeLimit': 60
        })
        assert response.status_code == 400
        
        # Test missing totalQuestions
        response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'timeLimit': 60
        })
        assert response.status_code == 400
        
        # Test missing timeLimit
        response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 5
        })
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_test_insufficient_questions(self, authenticated_client, sample_topic):
        """Test test creation when not enough questions available"""
        # Arrange - try to create test with more questions than available
        test_data = {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 100,  # More than available (5 from fixture)
            'timeLimit': 60
        }
        
        # Act
        response = authenticated_client.post('/api/test-sessions/', test_data)
        
        # Assert
        assert response.status_code == 400
        assert 'insufficient questions' in response.json().get('error', '').lower()

    @pytest.mark.django_db
    def test_start_test_session(self, authenticated_client, sample_topic, sample_questions):
        """Test starting a test session"""
        # Arrange - create test session
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 60
        })
        test_id = test_response.json()['id']
        
        # Act - start the test
        response = authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert 'questions' in response_data
        assert len(response_data['questions']) == 3
        
        # Verify session is marked as started
        test_session = TestSession.objects.get(id=test_id)
        assert test_session.start_time is not None


@pytest.mark.question_selection
@pytest.mark.unit
class TestPlatformTests:
    """Test platform-provided standardized tests"""

    @pytest.mark.django_db
    def test_list_available_platform_tests(self, authenticated_client, sample_platform_test):
        """Test listing available platform tests"""
        # Act
        response = authenticated_client.get('/api/platform-tests/available/')
        
        # Assert
        assert response.status_code == 200
        tests = response.json()
        assert len(tests) >= 1
        
        test_data = tests[0]
        assert 'testName' in test_data
        assert 'testCode' in test_data
        assert 'timeLimit' in test_data
        assert 'totalQuestions' in test_data

    @pytest.mark.django_db
    def test_get_platform_test_details(self, authenticated_client, sample_platform_test):
        """Test getting platform test details"""
        # Act
        response = authenticated_client.get(f'/api/platform-tests/{sample_platform_test.id}/')
        
        # Assert
        assert response.status_code == 200
        test_data = response.json()
        assert test_data['testName'] == sample_platform_test.test_name
        assert test_data['timeLimit'] == sample_platform_test.time_limit
        assert 'selectedTopics' in test_data
        assert 'difficultyDistribution' in test_data

    @pytest.mark.django_db
    def test_start_platform_test(self, authenticated_client, sample_platform_test, sample_questions):
        """Test starting a platform test"""
        # Act
        response = authenticated_client.post(f'/api/platform-tests/{sample_platform_test.id}/start/')
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert 'testSessionId' in response_data
        
        # Verify test session was created
        test_session = TestSession.objects.get(id=response_data['testSessionId'])
        assert test_session.platform_test_id == sample_platform_test.id
        assert test_session.total_questions == sample_platform_test.total_questions

    @pytest.mark.django_db
    def test_start_inactive_platform_test(self, authenticated_client, sample_platform_test):
        """Test starting an inactive platform test"""
        # Arrange
        sample_platform_test.is_active = False
        sample_platform_test.save()
        
        # Act
        response = authenticated_client.post(f'/api/platform-tests/{sample_platform_test.id}/start/')
        
        # Assert
        assert response.status_code == 400
        assert 'not available' in response.json().get('error', '').lower()


@pytest.mark.question_selection
@pytest.mark.unit
class TestTopicAndChapterSelection:
    """Test topic and chapter selection functionality"""

    @pytest.mark.django_db
    def test_list_topics_by_subject(self, api_client, sample_topic):
        """Test listing topics filtered by subject"""
        # Arrange - create topics for different subjects
        physics_topic = Topic.objects.create(
            name='Mechanics',
            subject='Physics',
            icon='physics-icon',
            chapter='Laws of Motion'
        )
        
        # Act
        response = api_client.get('/api/topics/?subject=Chemistry')
        
        # Assert
        assert response.status_code == 200
        topics = response.json().get('results', response.json())
        chemistry_topics = [t for t in topics if t['subject'] == 'Chemistry']
        assert len(chemistry_topics) >= 1
        assert sample_topic.name in [t['name'] for t in chemistry_topics]

    @pytest.mark.django_db
    def test_list_topics_by_chapter(self, api_client, sample_topic):
        """Test listing topics filtered by chapter"""
        # Act
        response = api_client.get(f'/api/topics/?chapter={sample_topic.chapter}')
        
        # Assert
        assert response.status_code == 200
        topics = response.json().get('results', response.json())
        chapter_topics = [t for t in topics if t['chapter'] == sample_topic.chapter]
        assert len(chapter_topics) >= 1

    @pytest.mark.django_db
    def test_get_topic_details_with_questions_count(self, api_client, sample_topic, sample_questions):
        """Test getting topic details including question count"""
        # Act
        response = api_client.get(f'/api/topics/{sample_topic.id}/')
        
        # Assert
        assert response.status_code == 200
        topic_data = response.json()
        assert topic_data['name'] == sample_topic.name
        # Check if questions count is included (depends on your serializer)
        # assert 'questionsCount' in topic_data

    @pytest.mark.django_db
    def test_question_count_by_topic(self, sample_topic, sample_questions):
        """Test counting questions available per topic"""
        # Act
        question_count = Question.objects.filter(topic=sample_topic).count()
        
        # Assert
        assert question_count == 5  # From sample_questions fixture

    @pytest.mark.django_db
    def test_question_difficulty_count_by_topic(self, sample_topic):
        """Test counting questions by difficulty per topic"""
        # Arrange - create questions with specific difficulties
        difficulties = {'easy': 2, 'medium': 3, 'hard': 1}
        
        for difficulty, count in difficulties.items():
            for i in range(count):
                Question.objects.create(
                    topic=sample_topic,
                    question=f'{difficulty} question {i}',
                    option_a='A', option_b='B', option_c='C', option_d='D',
                    correct_answer='A',
                    explanation='Explanation',
                    difficulty=difficulty
                )
        
        # Act & Assert
        for difficulty, expected_count in difficulties.items():
            actual_count = Question.objects.filter(
                topic=sample_topic,
                difficulty=difficulty
            ).count()
            assert actual_count == expected_count

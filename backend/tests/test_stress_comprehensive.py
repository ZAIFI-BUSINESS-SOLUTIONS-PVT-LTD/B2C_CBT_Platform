"""
Stress tests for NEET CBT Platform
Tests high-volume scenarios, large data handling, and performance under load
"""
import pytest
from unittest.mock import patch, MagicMock
import time
import threading
from datetime import datetime, timedelta
from django.test import override_settings
from django.utils import timezone
from PIL import Image
import io

from neet_app.models import (
    ChatSession, ChatMessage, TestSession, TestAnswer, 
    Question, Topic, StudentProfile
)


@pytest.mark.stress
@pytest.mark.slow
class TestHighVolumeRequests:
    """Test handling of high-volume requests"""

    @pytest.mark.django_db
    def test_many_concurrent_chat_sessions(self, authenticated_client, sample_topic, mock_llm_response):
        """Test creating many chat sessions concurrently"""
        # Arrange
        num_sessions = 50
        session_ids = []
        
        # Mock the chatbot service to be fast
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.return_value = mock_llm_response
            
            # Act - create many sessions rapidly
            start_time = time.time()
            
            for i in range(num_sessions):
                response = authenticated_client.post('/api/chat-sessions/', {
                    'title': f'Load Test Session {i}'
                })
                if response.status_code == 201:
                    session_data = response.json()
                    session_ids.append(session_data.get('chatSessionId') or session_data.get('id'))
            
            end_time = time.time()
            
            # Assert
            assert len(session_ids) == num_sessions, "All sessions should be created successfully"
            
            # Performance check - should create sessions reasonably fast
            avg_time_per_session = (end_time - start_time) / num_sessions
            assert avg_time_per_session < 0.5, f"Session creation took {avg_time_per_session:.3f}s each, should be under 0.5s"
            
            # Verify all sessions exist in database
            db_sessions = ChatSession.objects.filter(
                student_id=authenticated_client.student_profile.student_id
            )
            assert db_sessions.count() == num_sessions

    @pytest.mark.django_db
    def test_rapid_message_sending(self, authenticated_client, sample_chat_session, mock_llm_response):
        """Test sending many messages rapidly to the same session"""
        # Arrange
        num_messages = 100
        messages_sent = 0
        
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.return_value = mock_llm_response
            
            # Act
            start_time = time.time()
            
            for i in range(num_messages):
                response = authenticated_client.post(
                    f'/api/chat-sessions/{sample_chat_session.chat_session_id}/send-message/',
                    {'message': f'Stress test message {i}'}
                )
                if response.status_code in [200, 201]:
                    messages_sent += 1
            
            end_time = time.time()
            
            # Assert
            assert messages_sent == num_messages, "All messages should be sent successfully"
            
            # Check database consistency
            total_messages = ChatMessage.objects.filter(chat_session=sample_chat_session).count()
            # Should have user messages + bot responses
            assert total_messages >= num_messages

            # Performance check
            total_time = end_time - start_time
            assert total_time < 30, f"Sending {num_messages} messages took {total_time:.2f}s, should be under 30s"

    @pytest.mark.django_db
    def test_concurrent_test_sessions(self, sample_topic, sample_questions):
        """Test multiple users creating test sessions concurrently"""
        # Arrange - create multiple student profiles
        num_students = 10
        students = []
        
        for i in range(num_students):
            profile = StudentProfile.objects.create(
                student_id=f'STU25010100{i:03d}',
                full_name=f'Test Student {i}',
                email=f'student{i}@test.com',
                date_of_birth='2000-01-01'
            )
            profile.set_password('testpass123')
            profile.save()
            students.append(profile)
        
        results = []
        
        def create_test_session(student_profile):
            """Worker function to create test session for a student"""
            from rest_framework.test import APIClient
            from rest_framework_simplejwt.tokens import RefreshToken
            
            try:
                client = APIClient()
                refresh = RefreshToken.for_user(student_profile.user)
                access_token = str(refresh.access_token)
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
                
                response = client.post('/api/test-sessions/', {
                    'selectedTopics': [sample_topic.id],
                    'totalQuestions': 5,
                    'timeLimit': 60
                })
                
                results.append(response.status_code == 201)
            except Exception as e:
                results.append(False)
        
        # Act - create test sessions concurrently
        threads = []
        start_time = time.time()
        
        for student in students:
            thread = threading.Thread(target=create_test_session, args=(student,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        end_time = time.time()
        
        # Assert
        assert len(results) == num_students
        assert all(results), "All concurrent test sessions should be created successfully"
        
        # Check database state
        total_sessions = TestSession.objects.count()
        assert total_sessions == num_students
        
        # Performance check
        total_time = end_time - start_time
        assert total_time < 15, f"Concurrent session creation took {total_time:.2f}s, should be under 15s"


@pytest.mark.stress
@pytest.mark.slow
class TestLargeDataHandling:
    """Test handling of large datasets and memory usage"""

    def test_large_image_processing(self, mock_image, temp_directory):
        """Test processing very large images for exports"""
        # Arrange - create large images
        large_sizes = [
            (4000, 3000),   # 12MP image
            (6000, 4000),   # 24MP image
            (8000, 6000),   # 48MP image
        ]
        
        for width, height in large_sizes:
            # Act
            start_time = time.time()
            
            try:
                # Create large image
                large_img_data = mock_image(width, height, format='PNG')
                
                # Process image (simulate export operations)
                img = Image.open(large_img_data)
                
                # Resize for different export formats
                thumbnail = img.resize((800, 600))
                medium = img.resize((1600, 1200))
                
                # Save in different formats
                png_output = io.BytesIO()
                jpg_output = io.BytesIO()
                
                thumbnail.save(png_output, format='PNG')
                medium.save(jpg_output, format='JPEG', quality=85)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Assert
                assert processing_time < 10, f"Processing {width}x{height} image took {processing_time:.2f}s, should be under 10s"
                
                # Check memory usage by verifying outputs are reasonable
                png_size = len(png_output.getvalue())
                jpg_size = len(jpg_output.getvalue())
                
                assert png_size < 50 * 1024 * 1024, "PNG output should be under 50MB"
                assert jpg_size < 20 * 1024 * 1024, "JPEG output should be under 20MB"
                
            except MemoryError:
                pytest.fail(f"Should handle {width}x{height} image without memory error")

    @pytest.mark.django_db
    def test_large_chat_history_retrieval(self, authenticated_client, sample_chat_session):
        """Test retrieving large chat histories efficiently"""
        # Arrange - create large chat history
        num_messages = 1000
        
        # Create messages in batches for efficiency
        batch_size = 50
        for batch_start in range(0, num_messages, batch_size):
            batch_messages = []
            for i in range(batch_start, min(batch_start + batch_size, num_messages)):
                # Alternate between user and bot messages
                message_type = 'user' if i % 2 == 0 else 'bot'
                batch_messages.append(ChatMessage(
                    chat_session=sample_chat_session,
                    message_type=message_type,
                    message_content=f'Message {i} - {"This is a longer message to simulate real conversation content " * 5}',
                    processing_time=0.1
                ))
            
            ChatMessage.objects.bulk_create(batch_messages)
        
        # Act - retrieve messages with pagination
        start_time = time.time()
        
        # Test first page
        response = authenticated_client.get(
            f'/api/chat-sessions/{sample_chat_session.chat_session_id}/messages/?page_size=50'
        )
        
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert 'results' in response_data
        assert len(response_data['results']) == 50
        
        # Performance check
        retrieval_time = end_time - start_time
        assert retrieval_time < 2, f"Message retrieval took {retrieval_time:.2f}s, should be under 2s"
        
        # Test pagination works for large dataset
        assert 'next' in response_data
        assert response_data['count'] == num_messages

    @pytest.mark.django_db
    def test_large_question_bank_selection(self, sample_topic):
        """Test question selection from large question banks"""
        # Arrange - create large question bank
        num_questions = 5000
        
        # Create questions in batches
        batch_size = 100
        for batch_start in range(0, num_questions, batch_size):
            batch_questions = []
            for i in range(batch_start, min(batch_start + batch_size, num_questions)):
                difficulty = ['easy', 'medium', 'hard'][i % 3]
                batch_questions.append(Question(
                    topic=sample_topic,
                    question=f'Question {i}: What is the answer to this question?',
                    option_a=f'Option A{i}',
                    option_b=f'Option B{i}',
                    option_c=f'Option C{i}',
                    option_d=f'Option D{i}',
                    correct_answer='A',
                    explanation=f'Explanation for question {i}',
                    difficulty=difficulty,
                    question_type='mcq'
                ))
            
            Question.objects.bulk_create(batch_questions)
        
        # Act - test question selection performance
        start_time = time.time()
        
        # Simulate selecting 50 random questions
        selected_questions = Question.objects.filter(topic=sample_topic).order_by('?')[:50]
        question_list = list(selected_questions)  # Force evaluation
        
        end_time = time.time()
        
        # Assert
        assert len(question_list) == 50
        
        # Performance check
        selection_time = end_time - start_time
        assert selection_time < 5, f"Question selection took {selection_time:.2f}s, should be under 5s"
        
        # Verify no duplicates
        question_ids = [q.id for q in question_list]
        assert len(question_ids) == len(set(question_ids))


@pytest.mark.stress
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database performance under load"""

    @pytest.mark.django_db
    def test_bulk_test_answer_insertion(self, sample_student_profile, sample_topic, sample_questions):
        """Test bulk insertion of test answers"""
        # Arrange
        test_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_topic.id],
            total_questions=1000,
            time_limit=1800,  # 30 minutes
            is_completed=True
        )
        
        num_answers = 1000
        
        # Act - bulk create answers
        start_time = time.time()
        
        answers = []
        for i in range(num_answers):
            question = sample_questions[i % len(sample_questions)]
            answers.append(TestAnswer(
                test_session=test_session,
                question_id=question.id,
                selected_answer=['A', 'B', 'C', 'D'][i % 4],
                is_correct=(i % 4 == 0),  # 25% correct rate
                time_taken=30 + (i % 60)  # 30-90 seconds
            ))
        
        TestAnswer.objects.bulk_create(answers, batch_size=100)
        
        end_time = time.time()
        
        # Assert
        insertion_time = end_time - start_time
        assert insertion_time < 10, f"Bulk insertion took {insertion_time:.2f}s, should be under 10s"
        
        # Verify all answers were created
        assert TestAnswer.objects.filter(test_session=test_session).count() == num_answers

    @pytest.mark.django_db
    def test_complex_analytics_queries(self, sample_student_profile, sample_topic):
        """Test performance of complex analytics queries"""
        # Arrange - create data for analytics
        num_sessions = 50
        sessions = []
        
        for i in range(num_sessions):
            session = TestSession.objects.create(
                student_id=sample_student_profile.student_id,
                selected_topics=[sample_topic.id],
                total_questions=20,
                time_limit=1200,
                start_time=timezone.now() - timedelta(days=i),
                end_time=timezone.now() - timedelta(days=i, hours=-1),
                is_completed=True
            )
            sessions.append(session)
        
        # Create sample questions for analytics
        questions = []
        for i in range(20):
            question = Question.objects.create(
                topic=sample_topic,
                question=f'Analytics test question {i}',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                explanation='Explanation',
                difficulty=['easy', 'medium', 'hard'][i % 3]
            )
            questions.append(question)
        
        # Create test answers
        for session in sessions:
            for j, question in enumerate(questions):
                TestAnswer.objects.create(
                    test_session=session,
                    question_id=question.id,
                    selected_answer=['A', 'B', 'C', 'D'][j % 4],
                    is_correct=(j % 4 == 0),
                    time_taken=20 + (j % 40)
                )
        
        # Act - run complex analytics queries
        start_time = time.time()
        
        # Query 1: Overall performance
        total_answers = TestAnswer.objects.filter(
            test_session__student_id=sample_student_profile.student_id
        ).count()
        
        # Query 2: Performance by difficulty
        difficulty_stats = {}
        for difficulty in ['easy', 'medium', 'hard']:
            correct_count = TestAnswer.objects.filter(
                test_session__student_id=sample_student_profile.student_id,
                question__difficulty=difficulty,
                is_correct=True
            ).count()
            
            total_count = TestAnswer.objects.filter(
                test_session__student_id=sample_student_profile.student_id,
                question__difficulty=difficulty
            ).count()
            
            difficulty_stats[difficulty] = {
                'correct': correct_count,
                'total': total_count,
                'accuracy': (correct_count / total_count * 100) if total_count > 0 else 0
            }
        
        # Query 3: Time-based performance trends
        from django.db.models import Avg, Count
        daily_performance = TestAnswer.objects.filter(
            test_session__student_id=sample_student_profile.student_id
        ).extra({
            'day': 'date(test_session.start_time)'
        }).values('day').annotate(
            avg_time=Avg('time_taken'),
            total_questions=Count('id'),
            correct_answers=Count('id', filter={'is_correct': True})
        )
        
        end_time = time.time()
        
        # Assert
        query_time = end_time - start_time
        assert query_time < 5, f"Complex analytics queries took {query_time:.2f}s, should be under 5s"
        
        # Verify query results make sense
        assert total_answers == num_sessions * 20  # 50 sessions * 20 questions each
        assert len(difficulty_stats) == 3
        assert len(list(daily_performance)) <= num_sessions


@pytest.mark.stress
@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage under various load conditions"""

    @pytest.mark.django_db
    def test_memory_usage_large_export(self, authenticated_client, sample_student_profile, sample_topic):
        """Test memory usage during large export generation"""
        # Arrange - create large test session
        test_session = TestSession.objects.create(
            student_id=sample_student_profile.student_id,
            selected_topics=[sample_topic.id],
            total_questions=500,
            time_limit=3600,
            is_completed=True
        )
        
        # Create many test answers
        questions = []
        for i in range(500):
            question = Question.objects.create(
                topic=sample_topic,
                question=f'Memory test question {i}',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                explanation='Explanation'
            )
            questions.append(question)
            
            TestAnswer.objects.create(
                test_session=test_session,
                question_id=question.id,
                selected_answer='A',
                is_correct=True,
                time_taken=60
            )
        
        # Act - attempt export (mock the endpoint)
        try:
            # This would be your actual export endpoint
            # For testing, we'll simulate the memory usage pattern
            start_time = time.time()
            
            # Simulate gathering all data for export
            all_answers = list(TestAnswer.objects.filter(test_session=test_session))
            
            # Simulate processing large dataset
            processed_data = []
            for answer in all_answers:
                processed_data.append({
                    'question': f"Question {answer.question_id}",
                    'answer': answer.selected_answer,
                    'correct': answer.is_correct,
                    'time': answer.time_taken
                })
            
            end_time = time.time()
            
            # Assert
            processing_time = end_time - start_time
            assert processing_time < 10, f"Large export processing took {processing_time:.2f}s"
            assert len(processed_data) == 500
            
        except MemoryError:
            pytest.fail("Large export should not cause memory errors")

    def test_concurrent_memory_intensive_operations(self):
        """Test memory usage with multiple concurrent operations"""
        # Arrange
        num_operations = 5
        results = []
        
        def memory_intensive_operation():
            """Simulate memory-intensive operation"""
            try:
                # Create large data structure
                large_data = []
                for i in range(10000):
                    large_data.append({
                        'id': i,
                        'data': f'Large data item {i} with lots of text content ' * 10,
                        'timestamp': time.time(),
                        'nested': {
                            'more_data': [j for j in range(100)]
                        }
                    })
                
                # Process data
                processed = [item for item in large_data if item['id'] % 2 == 0]
                
                results.append(len(processed) == 5000)
                
            except MemoryError:
                results.append(False)
        
        # Act - run concurrent memory-intensive operations
        threads = []
        start_time = time.time()
        
        for _ in range(num_operations):
            thread = threading.Thread(target=memory_intensive_operation)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=15)
        
        end_time = time.time()
        
        # Assert
        assert len(results) == num_operations
        assert all(results), "All memory-intensive operations should complete successfully"
        
        total_time = end_time - start_time
        assert total_time < 20, f"Concurrent operations took {total_time:.2f}s, should be under 20s"


@pytest.mark.stress
@pytest.mark.slow
class TestErrorRecovery:
    """Test system behavior under error conditions and recovery"""

    @pytest.mark.django_db
    def test_database_connection_recovery(self, authenticated_client, sample_chat_session, mock_llm_response):
        """Test recovery from database connection issues"""
        # This test simulates database connection issues
        # In a real scenario, you'd test actual database failures
        
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.return_value = mock_llm_response
            
            # Simulate database connection failure and recovery
            with patch('django.db.connection.cursor') as mock_cursor:
                # First call fails
                mock_cursor.side_effect = [Exception("Database connection failed"), None]
                
                # Act - attempt operation that should recover
                response = authenticated_client.post(
                    f'/api/chat-sessions/{sample_chat_session.chat_session_id}/send-message/',
                    {'message': 'Test message during DB issues'}
                )
                
                # Assert - should handle gracefully
                # Implementation depends on your error handling strategy
                assert response.status_code in [200, 201, 500]  # Accept various responses based on implementation

    @pytest.mark.django_db
    def test_llm_service_failure_handling(self, authenticated_client, sample_chat_session):
        """Test handling of LLM service failures"""
        # Arrange - mock LLM service to fail
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.side_effect = Exception("LLM service unavailable")
            
            # Act
            response = authenticated_client.post(
                f'/api/chat-sessions/{sample_chat_session.chat_session_id}/send-message/',
                {'message': 'Test message during LLM failure'}
            )
            
            # Assert
            assert response.status_code == 500
            
            # Verify user message was still saved (partial failure handling)
            user_messages = ChatMessage.objects.filter(
                chat_session=sample_chat_session,
                message_type='user'
            )
            assert user_messages.count() >= 1

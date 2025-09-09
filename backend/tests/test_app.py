"""
Main application tests for NEET CBT Platform
Integration tests covering complete user workflows and end-to-end scenarios
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from neet_app.models import (
    ChatSession, ChatMessage, TestSession, TestAnswer, 
    Question, Topic, StudentProfile, PlatformTest
)


@pytest.mark.integration
class TestCompleteUserJourney:
    """Test complete user journeys from login to completion"""

    @pytest.mark.django_db
    def test_complete_chat_journey(self, api_client, sample_student_profile, mock_llm_response):
        """Test complete chat journey: login -> create session -> send messages -> deactivate"""
        # Arrange - login
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(sample_student_profile.user)
        access_token = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.return_value = mock_llm_response
            
            # Step 1: Create chat session
            session_response = api_client.post('/api/chat-sessions/', {
                'title': 'Complete Journey Test'
            })
            assert session_response.status_code == 201
            session_id = session_response.json().get('chatSessionId') or session_response.json().get('id')
            
            # Step 2: Send first message (should update title)
            first_message_response = api_client.post(
                f'/api/chat-sessions/{session_id}/send-message/',
                {'message': 'What is photosynthesis and how does it work?'}
            )
            assert first_message_response.status_code in [200, 201]
            
            # Step 3: Send follow-up messages
            for i in range(3):
                response = api_client.post(
                    f'/api/chat-sessions/{session_id}/send-message/',
                    {'message': f'Follow-up question {i + 1}'}
                )
                assert response.status_code in [200, 201]
            
            # Step 4: Retrieve message history
            messages_response = api_client.get(f'/api/chat-sessions/{session_id}/messages/')
            assert messages_response.status_code == 200
            messages = messages_response.json().get('results', messages_response.json())
            assert len(messages) >= 8  # 4 user + 4 bot messages
            
            # Step 5: Get chat statistics
            stats_response = api_client.get('/api/chatbot/statistics/')
            assert stats_response.status_code == 200
            stats = stats_response.json()
            assert stats['totalSessions'] >= 1
            assert stats['totalMessagesSent'] >= 4
            
            # Step 6: Deactivate session
            deactivate_response = api_client.patch(
                f'/api/chat-sessions/{session_id}/',
                {'isActive': False}
            )
            assert deactivate_response.status_code == 200
            
            # Verify session is deactivated
            session = ChatSession.objects.get(chat_session_id=session_id)
            assert session.is_active == False

    @pytest.mark.django_db
    def test_complete_test_taking_journey(self, api_client, sample_student_profile, sample_topic, sample_questions):
        """Test complete test-taking journey: login -> create test -> take test -> view results"""
        # Arrange - login
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(sample_student_profile.user)
        access_token = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Step 1: Browse available topics
        topics_response = api_client.get('/api/topics/')
        assert topics_response.status_code == 200
        topics = topics_response.json().get('results', topics_response.json())
        assert len(topics) >= 1
        
        # Step 2: Create custom test
        test_response = api_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 60,
            'testType': 'practice'
        })
        assert test_response.status_code == 201
        test_id = test_response.json()['id']
        
        # Step 3: Start test
        start_response = api_client.post(f'/api/test-sessions/{test_id}/start/')
        assert start_response.status_code == 200
        test_data = start_response.json()
        assert 'questions' in test_data
        questions = test_data['questions']
        assert len(questions) == 3
        
        # Step 4: Submit answers
        for i, question_data in enumerate(questions):
            answer_response = api_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
                'questionId': question_data['id'],
                'selectedAnswer': 'A',  # Always select A for simplicity
                'timeTaken': 30 + (i * 5)  # Varying time
            })
            assert answer_response.status_code == 201
        
        # Step 5: Complete test
        complete_response = api_client.post(f'/api/test-sessions/{test_id}/complete/')
        assert complete_response.status_code == 200
        
        # Step 6: View results
        results_response = api_client.get(f'/api/test-sessions/{test_id}/results/')
        assert results_response.status_code == 200
        results = results_response.json()
        assert 'score' in results or 'accuracy' in results
        assert 'totalQuestions' in results
        
        # Verify database state
        test_session = TestSession.objects.get(id=test_id)
        assert test_session.is_completed == True
        assert test_session.end_time is not None
        
        answers = TestAnswer.objects.filter(test_session=test_session)
        assert answers.count() == 3

    @pytest.mark.django_db
    def test_platform_test_journey(self, api_client, sample_student_profile, sample_platform_test, sample_questions):
        """Test taking a platform-provided standardized test"""
        # Arrange - login
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(sample_student_profile.user)
        access_token = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Step 1: Browse available platform tests
        platform_tests_response = api_client.get('/api/platform-tests/available/')
        assert platform_tests_response.status_code == 200
        tests = platform_tests_response.json()
        assert len(tests) >= 1
        
        # Step 2: Get test details
        test_details_response = api_client.get(f'/api/platform-tests/{sample_platform_test.id}/')
        assert test_details_response.status_code == 200
        test_details = test_details_response.json()
        assert test_details['testName'] == sample_platform_test.test_name
        
        # Step 3: Start platform test
        start_platform_response = api_client.post(f'/api/platform-tests/{sample_platform_test.id}/start/')
        assert start_platform_response.status_code == 201
        test_session_id = start_platform_response.json()['testSessionId']
        
        # Step 4: Take a few questions (abbreviated for platform test)
        # In a real scenario, this would be the full test
        for i in range(min(3, len(sample_questions))):
            api_client.post(f'/api/test-sessions/{test_session_id}/submit-answer/', {
                'questionId': sample_questions[i].id,
                'selectedAnswer': 'A',
                'timeTaken': 45
            })
        
        # Step 5: Complete platform test
        complete_response = api_client.post(f'/api/test-sessions/{test_session_id}/complete/')
        assert complete_response.status_code == 200
        
        # Verify platform test session
        test_session = TestSession.objects.get(id=test_session_id)
        assert test_session.platform_test_id == sample_platform_test.id


@pytest.mark.integration
class TestCrossFunctionalityIntegration:
    """Test integration between different system components"""

    @pytest.mark.django_db
    def test_chat_and_test_integration(self, authenticated_client, sample_topic, sample_questions, mock_llm_response):
        """Test integration between chatbot and test functionality"""
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            # Mock chatbot to suggest test creation
            mock_service.return_value = {
                **mock_llm_response,
                'intent': 'suggest_test',
                'response': 'I recommend taking a test on this topic to practice.',
                'has_personalized_data': True
            }
            
            # Step 1: Chat about a topic
            chat_response = authenticated_client.post('/api/chat-sessions/', {
                'title': 'Topic Discussion'
            })
            session_id = chat_response.json().get('chatSessionId') or chat_response.json().get('id')
            
            message_response = authenticated_client.post(
                f'/api/chat-sessions/{session_id}/send-message/',
                {'message': 'I want to practice organic chemistry questions'}
            )
            assert message_response.status_code in [200, 201]
            
            # Step 2: Create test based on chat topic
            test_response = authenticated_client.post('/api/test-sessions/', {
                'selectedTopics': [sample_topic.id],
                'totalQuestions': 2,
                'timeLimit': 60,
                'metadata': {
                    'source': 'chat_recommendation',
                    'chat_session_id': session_id
                }
            })
            assert test_response.status_code == 201
            test_id = test_response.json()['id']
            
            # Step 3: Complete test
            start_response = authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
            questions = start_response.json()['questions']
            
            for question in questions:
                authenticated_client.post(f'/api/test-sessions/{test_id}/submit-answer/', {
                    'questionId': question['id'],
                    'selectedAnswer': 'A',
                    'timeTaken': 40
                })
            
            authenticated_client.post(f'/api/test-sessions/{test_id}/complete/')
            
            # Step 4: Chat about test results
            results_message_response = authenticated_client.post(
                f'/api/chat-sessions/{session_id}/send-message/',
                {'message': 'How did I perform on that test?'}
            )
            assert results_message_response.status_code in [200, 201]

    @pytest.mark.django_db
    def test_insights_and_test_creation_integration(self, authenticated_client, sample_student_profile, sample_topic, sample_questions):
        """Test integration between insights and adaptive test creation"""
        # Step 1: Create test history with mixed performance
        for i in range(3):
            test_session = TestSession.objects.create(
                student_id=sample_student_profile.student_id,
                selected_topics=[sample_topic.id],
                total_questions=3,
                time_limit=60,
                start_time=timezone.now() - timedelta(days=i+1),
                end_time=timezone.now() - timedelta(days=i+1, hours=-1),
                is_completed=True
            )
            
            # Create answers with varying performance
            for j, question in enumerate(sample_questions[:3]):
                # Performance degrades over time for this test
                is_correct = (i == 0 and j < 2) or (i == 1 and j < 1) or (i == 2 and False)
                
                TestAnswer.objects.create(
                    test_session=test_session,
                    question_id=question.id,
                    selected_answer='A' if is_correct else 'B',
                    is_correct=is_correct,
                    time_taken=30 + (j * 10)
                )
        
        # Step 2: Get insights
        insights_response = authenticated_client.get('/api/insights/student/')
        assert insights_response.status_code == 200
        insights = insights_response.json()
        
        # Step 3: Create adaptive test based on insights
        # This test would prioritize topics/difficulty based on performance
        adaptive_test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 5,
            'timeLimit': 120,
            'adaptiveMode': True,  # Use insights for question selection
            'metadata': {
                'source': 'adaptive_recommendation'
            }
        })
        assert adaptive_test_response.status_code == 201

    @pytest.mark.django_db
    def test_authentication_across_features(self, api_client, sample_student_profile):
        """Test that authentication works consistently across all features"""
        # Test without authentication first
        endpoints_requiring_auth = [
            '/api/chat-sessions/',
            '/api/test-sessions/',
            '/api/insights/student/',
            '/api/chatbot/statistics/'
        ]
        
        for endpoint in endpoints_requiring_auth:
            response = api_client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        # Now test with authentication
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(sample_student_profile.user)
        access_token = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        for endpoint in endpoints_requiring_auth:
            response = api_client.get(endpoint)
            assert response.status_code in [200, 204], f"Authenticated request to {endpoint} should succeed"


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across the application"""

    @pytest.mark.django_db
    def test_student_data_consistency(self, authenticated_client, sample_student_profile, sample_topic, sample_questions):
        """Test that student data remains consistent across operations"""
        student_id = sample_student_profile.student_id
        
        # Create multiple types of records for the student
        # Chat session
        chat_response = authenticated_client.post('/api/chat-sessions/', {
            'title': 'Consistency Test Chat'
        })
        chat_session_id = chat_response.json().get('chatSessionId') or chat_response.json().get('id')
        
        # Test session
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 2,
            'timeLimit': 60
        })
        test_session_id = test_response.json()['id']
        
        # Verify all records are associated with correct student
        chat_session = ChatSession.objects.get(chat_session_id=chat_session_id)
        test_session = TestSession.objects.get(id=test_session_id)
        
        assert chat_session.student_id == student_id
        assert test_session.student_id == student_id
        
        # Test that student cannot access other students' data
        other_student = StudentProfile.objects.create(
            user_id=sample_student_profile.user_id + 1000,  # Different user
            student_id='STU25010199999',
            full_name='Other Student',
            email='other@test.com'
        )
        
        other_chat = ChatSession.objects.create(
            student_id=other_student.student_id,
            chat_session_id='other_session_123',
            session_title='Other Chat'
        )
        
        # Try to access other student's chat
        other_chat_response = authenticated_client.get(f'/api/chat-sessions/{other_chat.chat_session_id}/')
        assert other_chat_response.status_code in [403, 404]

    @pytest.mark.django_db
    def test_test_session_data_integrity(self, authenticated_client, sample_student_profile, sample_topic, sample_questions):
        """Test test session data integrity throughout the test lifecycle"""
        # Create test
        test_response = authenticated_client.post('/api/test-sessions/', {
            'selectedTopics': [sample_topic.id],
            'totalQuestions': 3,
            'timeLimit': 90
        })
        test_id = test_response.json()['id']
        
        # Start test
        start_response = authenticated_client.post(f'/api/test-sessions/{test_id}/start/')
        questions = start_response.json()['questions']
        
        # Submit answers
        submitted_answers = []
        for i, question in enumerate(questions):
            answer_data = {
                'questionId': question['id'],
                'selectedAnswer': ['A', 'B', 'C'][i],  # Different answers
                'timeTaken': 25 + (i * 10)
            }
            
            answer_response = authenticated_client.post(
                f'/api/test-sessions/{test_id}/submit-answer/',
                answer_data
            )
            assert answer_response.status_code == 201
            submitted_answers.append(answer_data)
        
        # Complete test
        authenticated_client.post(f'/api/test-sessions/{test_id}/complete/')
        
        # Verify data integrity
        test_session = TestSession.objects.get(id=test_id)
        test_answers = TestAnswer.objects.filter(test_session=test_session)
        
        assert test_answers.count() == 3
        assert test_session.is_completed == True
        assert test_session.start_time is not None
        assert test_session.end_time is not None
        
        # Verify each answer matches what was submitted
        for i, answer in enumerate(test_answers.order_by('id')):
            submitted = submitted_answers[i]
            assert answer.question_id == submitted['questionId']
            assert answer.selected_answer == submitted['selectedAnswer']
            assert answer.time_taken == submitted['timeTaken']

    @pytest.mark.django_db
    def test_concurrent_operation_consistency(self, authenticated_client, sample_chat_session, mock_llm_response):
        """Test data consistency under concurrent operations"""
        import threading
        
        results = []
        
        def send_message(message_num):
            """Send a message concurrently"""
            try:
                with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
                    mock_service.return_value = {
                        **mock_llm_response,
                        'message_id': f'concurrent_msg_{message_num}'
                    }
                    
                    response = authenticated_client.post(
                        f'/api/chat-sessions/{sample_chat_session.chat_session_id}/send-message/',
                        {'message': f'Concurrent message {message_num}'}
                    )
                    results.append(response.status_code in [200, 201])
            except Exception:
                results.append(False)
        
        # Send multiple messages concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=send_message, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all operations succeeded
        assert len(results) == 5
        assert all(results), "All concurrent operations should succeed"
        
        # Verify data consistency in database
        messages = ChatMessage.objects.filter(chat_session=sample_chat_session)
        user_messages = messages.filter(message_type='user')
        bot_messages = messages.filter(message_type='bot')
        
        # Should have user and bot messages (exact count depends on timing)
        assert user_messages.count() >= 5
        assert bot_messages.count() >= 5


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across integrated components"""

    @pytest.mark.django_db
    def test_partial_failure_handling(self, authenticated_client, sample_chat_session):
        """Test handling of partial failures in multi-step operations"""
        # Test scenario where user message is saved but bot response fails
        with patch('neet_app.services.chatbot_service_refactored.NeetChatbotService.generate_response') as mock_service:
            mock_service.side_effect = Exception("Simulated LLM failure")
            
            initial_message_count = ChatMessage.objects.filter(chat_session=sample_chat_session).count()
            
            # Send message that will fail during bot response generation
            response = authenticated_client.post(
                f'/api/chat-sessions/{sample_chat_session.chat_session_id}/send-message/',
                {'message': 'This will cause a bot response failure'}
            )
            
            # Should return error status
            assert response.status_code == 500
            
            # But user message should still be saved (partial success)
            final_message_count = ChatMessage.objects.filter(chat_session=sample_chat_session).count()
            assert final_message_count == initial_message_count + 1
            
            # Verify user message was saved correctly
            user_message = ChatMessage.objects.filter(
                chat_session=sample_chat_session,
                message_type='user'
            ).last()
            assert user_message.message_content == 'This will cause a bot response failure'

    @pytest.mark.django_db
    def test_transaction_rollback_on_failure(self, authenticated_client, sample_student_profile, sample_topic, sample_questions):
        """Test that transactions are properly rolled back on failures"""
        # This test would verify that if test creation fails midway,
        # no partial data is left in the database
        
        # Mock a failure during test creation
        with patch('neet_app.models.TestSession.save') as mock_save:
            mock_save.side_effect = Exception("Simulated database failure")
            
            initial_session_count = TestSession.objects.count()
            
            # Attempt to create test (should fail)
            response = authenticated_client.post('/api/test-sessions/', {
                'selectedTopics': [sample_topic.id],
                'totalQuestions': 3,
                'timeLimit': 60
            })
            
            # Should return error
            assert response.status_code == 500
            
            # No new test session should be created
            final_session_count = TestSession.objects.count()
            assert final_session_count == initial_session_count
"""
Test configuration and fixtures for NEET CBT Platform
"""
import os
import sys
import django
from django.conf import settings

# Set up Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.test_settings')

# Configure Django if not already configured
if not settings.configured:
    django.setup()

import pytest
import tempfile
from django.contrib.auth.models import User
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken
from neet_app.models import StudentProfile
from rest_framework.test import APIClient
from PIL import Image
import io

from neet_app.models import (
    StudentProfile, Topic, Question, ChatSession, ChatMessage,
    TestSession, PlatformTest
)


@pytest.fixture
def api_client():
    """Provide DRF APIClient for testing REST endpoints"""
    return APIClient()


@pytest.fixture
def django_client():
    """Provide Django test client for basic HTTP requests"""
    return Client()


@pytest.fixture
def sample_student_profile():
    """Create a sample student profile with proper student_id format"""
    # Create student profile directly without User dependency
    student_profile = StudentProfile.objects.create(
        student_id='STU25010100001',  # Format: STU + YY + DDMM + ABC123
        full_name='Test Student',
        email='student@example.com',
        phone_number='1234567890',
        date_of_birth='2000-01-01'
    )
    # Set password using the StudentProfile's built-in method
    student_profile.set_password('studentpass123')
    student_profile.save()
    return student_profile


@pytest.fixture
def authenticated_client(api_client, sample_student_profile):
    """Provide authenticated API client with JWT token"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    # Since StudentProfile doesn't inherit from User, we need to create tokens differently
    # We'll manually create JWT token for the student
    refresh = RefreshToken()
    refresh['student_id'] = sample_student_profile.student_id
    refresh['email'] = sample_student_profile.email
    access_token = str(refresh.access_token)
    
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    api_client.student_profile = sample_student_profile
    return api_client


@pytest.fixture
def sample_topic():
    """Create a sample topic for testing"""
    return Topic.objects.create(
        name='Organic Chemistry',
        subject='Chemistry',
        icon='chemistry-icon',
        chapter='Hydrocarbons'
    )


@pytest.fixture
def sample_questions(sample_topic):
    """Create sample questions for testing"""
    questions = []
    for i in range(5):
        question = Question.objects.create(
            topic=sample_topic,
            question=f'What is the answer to question {i + 1}?',
            option_a=f'Option A{i + 1}',
            option_b=f'Option B{i + 1}',
            option_c=f'Option C{i + 1}',
            option_d=f'Option D{i + 1}',
            correct_answer='A',
            explanation=f'Explanation for question {i + 1}',
            difficulty='medium',
            question_type='mcq'
        )
        questions.append(question)
    return questions


@pytest.fixture
def sample_chat_session(sample_student_profile):
    """Create a sample chat session for testing"""
    return ChatSession.objects.create(
        student_id=sample_student_profile.student_id,
        chat_session_id='chat_session_test_001',
        session_title='Test Chat Session',
        is_active=True
    )


@pytest.fixture
def sample_chat_messages(sample_chat_session):
    """Create sample chat messages for testing"""
    messages = []
    # User message
    user_msg = ChatMessage.objects.create(
        chat_session=sample_chat_session,
        message_type='user',
        message_content='What is photosynthesis?',
        processing_time=0.1
    )
    messages.append(user_msg)
    
    # Bot response
    bot_msg = ChatMessage.objects.create(
        chat_session=sample_chat_session,
        message_type='bot',
        message_content='Photosynthesis is the process by which plants convert light energy into chemical energy.',
        sql_query='SELECT * FROM topics WHERE name LIKE "%photosynthesis%"',
        processing_time=0.5
    )
    messages.append(bot_msg)
    
    return messages


@pytest.fixture
def sample_platform_test(sample_topic):
    """Create a sample platform test for testing"""
    return PlatformTest.objects.create(
        test_name='NEET 2024 Mock Test',
        test_code='NEET_2024_MOCK_001',
        test_year=2024,
        test_type='Mock',
        description='Mock test for NEET 2024 preparation',
        instructions='Answer all questions within the time limit',
        time_limit=180,  # 3 hours in minutes
        total_questions=180,
        selected_topics=[sample_topic.id],
        question_distribution={'Chemistry': 45, 'Physics': 45, 'Biology': 90},
        difficulty_distribution={'easy': 30, 'medium': 50, 'hard': 20},
        is_active=True
    )


@pytest.fixture
def mock_image():
    """Create a mock image for testing export functionality"""
    def _create_image(width=800, height=600, color=(255, 255, 255), format='PNG'):
        img = Image.new('RGB', (width, height), color)
        bio = io.BytesIO()
        img.save(bio, format=format)
        bio.seek(0)
        return bio
    return _create_image


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing file operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for chatbot testing"""
    return {
        "success": True,
        "intent": "answer_question", 
        "response": "This is a mocked AI response for testing purposes.",
        "has_personalized_data": False,
        "processing_time": 0.25,
        "message_id": "mock_msg_001"
    }


def get_jwt_token_for_user(user):
    """Helper function to generate JWT token for user"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


# Mark database access for all tests using db fixture
pytestmark = pytest.mark.django_db
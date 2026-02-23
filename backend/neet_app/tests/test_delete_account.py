"""
Tests for the delete account functionality.
This test suite verifies that student account deletion works correctly
and removes all associated data from the database.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, date
from ..models import (
    StudentProfile, TestSession, TestAnswer, ReviewComment,
    ChatSession, ChatMessage, ChatMemory,
    TestSubjectZoneInsight, Notification, PasswordReset,
    StudentActivity, PaymentOrder, Topic, Question
)


class DeleteAccountTestCase(TestCase):
    """Test suite for account deletion endpoint"""
    
    def setUp(self):
        """Set up test data before each test"""
        self.client = APIClient()
        
        # Create a test student
        self.student = StudentProfile.objects.create(
            student_id='STU26190201ABC123',
            full_name='Test Student',
            email='test@example.com',
            phone_number='1234567890',
            date_of_birth=date(2000, 1, 1)
        )
        self.student.set_password('test_password')
        self.student.save()
        
        # Create test topic and question
        self.topic = Topic.objects.create(
            name='Test Topic',
            subject='Physics',
            icon='test-icon'
        )
        
        self.question = Question.objects.create(
            topic=self.topic,
            question='Test question?',
            option_a='A',
            option_b='B',
            option_c='C',
            option_d='D',
            correct_answer='A',
            explanation='Test explanation'
        )
        
        # Create test session
        self.test_session = TestSession.objects.create(
            student_id=self.student.student_id,
            test_type='custom',
            selected_topics=[self.topic.id],
            start_time=datetime.now(),
            total_questions=1,
            is_completed=True,
            correct_answers=1
        )
        
        # Create test answer
        self.test_answer = TestAnswer.objects.create(
            session=self.test_session,
            question=self.question,
            selected_answer='A',
            is_correct=True
        )
        
        # Create chat session
        self.chat_session = ChatSession.objects.create(
            student_id=self.student.student_id,
            chat_session_id='test_chat_123'
        )
        
        # Create chat message
        self.chat_message = ChatMessage.objects.create(
            chat_session=self.chat_session,
            message_type='user',
            message_content='Test message'
        )
        
        # Authenticate the client
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_delete_account_without_confirmation(self):
        """Test that deletion fails without proper confirmation"""
        url = '/api/student-profile/delete-account/'
        response = self.client.post(url, {'confirmation': 'WRONG'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Student should still exist
        self.assertTrue(StudentProfile.objects.filter(student_id=self.student.student_id).exists())
    
    def test_delete_account_success(self):
        """Test successful account deletion"""
        url = '/api/student-profile/delete-account/'
        
        # Verify data exists before deletion
        self.assertTrue(StudentProfile.objects.filter(student_id=self.student.student_id).exists())
        self.assertTrue(TestSession.objects.filter(student_id=self.student.student_id).exists())
        self.assertTrue(TestAnswer.objects.filter(session=self.test_session).exists())
        self.assertTrue(ChatSession.objects.filter(student_id=self.student.student_id).exists())
        self.assertTrue(ChatMessage.objects.filter(chat_session=self.chat_session).exists())
        
        # Delete account with proper confirmation
        response = self.client.post(url, {'confirmation': 'DELETE'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Account deleted successfully')
        
        # Verify all data has been deleted
        self.assertFalse(StudentProfile.objects.filter(student_id=self.student.student_id).exists())
        self.assertFalse(TestSession.objects.filter(student_id=self.student.student_id).exists())
        self.assertFalse(TestAnswer.objects.filter(session_id=self.test_session.id).exists())
        self.assertFalse(ChatSession.objects.filter(student_id=self.student.student_id).exists())
        self.assertFalse(ChatMessage.objects.filter(chat_session_id=self.chat_session.id).exists())
    
    def test_delete_account_unauthenticated(self):
        """Test that unauthenticated users cannot delete accounts"""
        # Remove authentication
        self.client.credentials()
        
        url = '/api/student-profile/delete-account/'
        response = self.client.post(url, {'confirmation': 'DELETE'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # Student should still exist
        self.assertTrue(StudentProfile.objects.filter(student_id=self.student.student_id).exists())
    
    def test_delete_account_removes_all_data(self):
        """Test that all related data is properly deleted"""
        # Create additional related data
        StudentActivity.objects.create(
            student=self.student,
            last_seen=datetime.now()
        )
        
        ChatMemory.objects.create(
            student=self.student,
            memory_type='long_term',
            content={'test': 'data'}
        )
        
        # StudentInsight model deprecated — not created in this test
        # Delete account
        url = '/api/student-profile/delete-account/'
        response = self.client.post(url, {'confirmation': 'DELETE'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all related data is deleted
        self.assertFalse(StudentActivity.objects.filter(student_id=self.student.student_id).exists())
        self.assertFalse(ChatMemory.objects.filter(student=self.student.student_id).exists())
        # StudentInsight model deprecated — no assertions for it

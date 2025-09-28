"""
Tests for Mobile OTP authentication functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from neet_app.models import StudentProfile
from neet_app.utils.otp import normalize_mobile, generate_otp, hash_otp, verify_otp_hash


class MobileOTPTestCase(TestCase):
    """Test cases for mobile OTP authentication"""
    
    def setUp(self):
        self.client = APIClient()
        self.mobile = "+919876543210"
        self.otp = "123456"
    
    def test_normalize_mobile(self):
        """Test mobile number normalization"""
        # Test cases for different input formats
        test_cases = [
            ("9876543210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
            ("98765 43210", "+919876543210"),
            ("invalid", None),
            ("123456789", None),  # Too short
        ]
        
        for input_mobile, expected in test_cases:
            result = normalize_mobile(input_mobile)
            self.assertEqual(result, expected, f"Failed for input: {input_mobile}")
    
    def test_otp_hashing(self):
        """Test OTP hashing and verification"""
        otp = "123456"
        otp_hash = hash_otp(otp)
        
        # Verify correct OTP
        self.assertTrue(verify_otp_hash(otp, otp_hash))
        
        # Verify incorrect OTP
        self.assertFalse(verify_otp_hash("654321", otp_hash))
    
    @patch('neet_app.utils.sms.send_otp_sms')
    @patch('neet_app.utils.otp.redis_set_otp')
    @patch('neet_app.utils.otp.check_rate_limit')
    @patch('neet_app.utils.otp.check_cooldown')
    def test_send_otp_success(self, mock_cooldown, mock_rate_limit, mock_redis_set, mock_sms):
        """Test successful OTP sending"""
        # Setup mocks
        mock_rate_limit.return_value = (False, 1, 5)  # Not rate limited
        mock_cooldown.return_value = (False, 0)  # No cooldown
        mock_redis_set.return_value = True
        mock_sms.return_value = {'success': True, 'message_id': 'test-msg-id'}
        
        # Make request
        response = self.client.post('/auth/send-otp/', {
            'mobile_number': self.mobile
        })
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['cooldown_seconds'], 30)
        
        # Verify mocks were called
        mock_sms.assert_called_once()
        mock_redis_set.assert_called_once()
    
    @patch('neet_app.utils.otp.check_rate_limit')
    def test_send_otp_rate_limit(self, mock_rate_limit):
        """Test OTP sending with rate limit exceeded"""
        # Setup rate limit exceeded
        mock_rate_limit.return_value = (True, 6, 5)
        
        response = self.client.post('/auth/send-otp/', {
            'mobile_number': self.mobile
        })
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('detail', response.data)
    
    def test_send_otp_invalid_mobile(self):
        """Test OTP sending with invalid mobile number"""
        response = self.client.post('/auth/send-otp/', {
            'mobile_number': 'invalid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
    
    @patch('neet_app.utils.otp.redis_get_otp_hash')
    @patch('neet_app.utils.otp.verify_otp_hash')
    @patch('neet_app.utils.otp.redis_delete_otp')
    def test_verify_otp_existing_user(self, mock_delete, mock_verify, mock_get_hash):
        """Test OTP verification for existing user"""
        # Create existing student
        student = StudentProfile.objects.create(
            student_id="TEST123456789",
            phone_number=self.mobile,
            is_active=True
        )
        
        # Setup mocks
        mock_get_hash.return_value = "dummy_hash"
        mock_verify.return_value = True
        mock_delete.return_value = True
        
        response = self.client.post('/auth/verify-otp/', {
            'mobile_number': self.mobile,
            'otp_code': self.otp
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('student', response.data)
        
        # Verify OTP was deleted
        mock_delete.assert_called_once()
    
    @patch('neet_app.utils.otp.redis_get_otp_hash')
    @patch('neet_app.utils.otp.verify_otp_hash')
    @patch('neet_app.utils.otp.redis_delete_otp')
    @patch('neet_app.utils.student_utils.generate_unique_student_id_for_mobile')
    def test_verify_otp_new_user(self, mock_gen_id, mock_delete, mock_verify, mock_get_hash):
        """Test OTP verification for new user (auto-create)"""
        # Setup mocks
        mock_get_hash.return_value = "dummy_hash"
        mock_verify.return_value = True
        mock_delete.return_value = True
        mock_gen_id.return_value = "MOB241226ABC123"
        
        response = self.client.post('/auth/verify-otp/', {
            'mobile_number': self.mobile,
            'otp_code': self.otp
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('student', response.data)
        
        # Check that new student was created
        student = StudentProfile.objects.get(phone_number=self.mobile)
        self.assertEqual(student.student_id, "MOB241226ABC123")
        self.assertEqual(student.auth_provider, 'mobile')
        self.assertTrue(student.is_active)
        
        # Check camelCase response format
        student_data = response.data['student']
        self.assertIn('studentId', student_data)
        self.assertIn('phoneNumber', student_data)
        self.assertIn('isProfileComplete', student_data)
        self.assertFalse(student_data['isProfileComplete'])  # No email/name/dob
    
    @patch('neet_app.utils.otp.redis_get_otp_hash')
    def test_verify_otp_expired(self, mock_get_hash):
        """Test OTP verification with expired OTP"""
        mock_get_hash.return_value = None  # No OTP found in Redis
        
        response = self.client.post('/auth/verify-otp/', {
            'mobile_number': self.mobile,
            'otp_code': self.otp
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
    
    @patch('neet_app.utils.otp.redis_get_otp_hash')
    @patch('neet_app.utils.otp.verify_otp_hash')
    def test_verify_otp_invalid(self, mock_verify, mock_get_hash):
        """Test OTP verification with invalid OTP"""
        mock_get_hash.return_value = "dummy_hash"
        mock_verify.return_value = False  # Invalid OTP
        
        response = self.client.post('/auth/verify-otp/', {
            'mobile_number': self.mobile,
            'otp_code': self.otp
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
    
    def test_verify_otp_invalid_format(self):
        """Test OTP verification with invalid OTP format"""
        test_cases = [
            "",  # Empty
            "12345",  # Too short
            "1234567",  # Too long
            "abcdef",  # Non-numeric
            "12345a",  # Mixed
        ]
        
        for invalid_otp in test_cases:
            response = self.client.post('/auth/verify-otp/', {
                'mobile_number': self.mobile,
                'otp_code': invalid_otp
            })
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('detail', response.data)


# Integration test to check if URLs are properly configured
class MobileOTPURLTestCase(TestCase):
    """Test URL configuration for mobile OTP endpoints"""
    
    def test_send_otp_url_exists(self):
        """Test that send OTP URL is configured"""
        url = reverse('auth-send-otp')
        self.assertEqual(url, '/auth/send-otp/')
    
    def test_verify_otp_url_exists(self):
        """Test that verify OTP URL is configured"""
        url = reverse('auth-verify-otp')
        self.assertEqual(url, '/auth/verify-otp/')


if __name__ == '__main__':
    pytest.main([__file__])
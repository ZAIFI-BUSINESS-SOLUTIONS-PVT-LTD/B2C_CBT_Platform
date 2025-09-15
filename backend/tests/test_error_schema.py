"""
Tests for standardized error schema and handling.

These tests ensure that all API endpoints return errors in the standardized format
and that the error handling system works correctly.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from neet_app.models import StudentProfile
from neet_app.errors import AppError
from neet_app.error_codes import ErrorCodes


@pytest.mark.django_db
class TestErrorSchema:
    """Test that all API errors follow the standardized schema"""

    def test_authentication_error_schema(self, api_client):
        """Test that authentication errors follow standard schema"""
        # Try to access protected endpoint without authentication
        response = api_client.get('/api/chat-sessions/')
        
        assert response.status_code == 401
        assert 'error' in response.json()
        
        error = response.json()['error']
        assert 'code' in error
        assert 'message' in error
        assert 'timestamp' in error
        assert error['code'] in [ErrorCodes.AUTH_REQUIRED, ErrorCodes.AUTH_TOKEN_INVALID]

    def test_validation_error_schema(self, api_client):
        """Test that validation errors follow standard schema"""
        # Try to login with missing credentials
        response = api_client.post('/api/auth/login/', {})
        
        assert response.status_code == 400
        assert 'error' in response.json()
        
        error = response.json()['error']
        assert 'code' in error
        assert 'message' in error
        assert 'timestamp' in error
        assert error['code'] == ErrorCodes.INVALID_INPUT

    def test_not_found_error_schema(self, api_client, authenticated_student):
        """Test that not found errors follow standard schema"""
        api_client.force_authenticate(user=authenticated_student)
        
        # Try to access non-existent resource
        response = api_client.get('/api/test-sessions/99999/')
        
        assert response.status_code == 404
        assert 'error' in response.json()
        
        error = response.json()['error']
        assert 'code' in error
        assert 'message' in error
        assert 'timestamp' in error
        assert error['code'] in [ErrorCodes.NOT_FOUND, ErrorCodes.TEST_SESSION_NOT_FOUND]

    def test_password_reset_error_schema(self, api_client):
        """Test password reset errors follow standard schema"""
        # Try to verify invalid token
        response = api_client.get('/api/auth/verify-reset-token/', {
            'email': 'test@example.com',
            'token': 'invalid-token'
        })
        
        assert response.status_code == 401
        assert 'error' in response.json()
        
        error = response.json()['error']
        assert 'code' in error
        assert 'message' in error
        assert 'timestamp' in error
        assert error['code'] == ErrorCodes.AUTH_TOKEN_INVALID

    def test_server_error_schema(self, api_client, authenticated_student):
        """Test that server errors follow standard schema"""
        # Authenticate to bypass auth checks
        api_client.force_authenticate(user=authenticated_student)
        
        # Mock a server error in a view
        with patch('neet_app.views.dashboard_views.dashboard_analytics') as mock_view:
            mock_view.side_effect = Exception("Database connection failed")
            
            response = api_client.get('/api/dashboard/analytics/')
            
            assert response.status_code == 500
            assert 'error' in response.json()
            
            error = response.json()['error']
            assert 'code' in error
            assert 'message' in error
            assert 'timestamp' in error
            assert error['code'] == ErrorCodes.SERVER_ERROR

    def test_app_error_handling(self, api_client):
        """Test that AppError instances are properly handled"""
        # This would typically be tested in a view that raises AppError
        # For this test, we'll test the error creation and serialization
        
        app_error = AppError(
            code=ErrorCodes.INVALID_INPUT,
            message="Test validation error",
            details={"field": "email"}
        )
        
        error_dict = app_error.to_dict()
        
        assert 'error' in error_dict
        assert error_dict['error']['code'] == ErrorCodes.INVALID_INPUT
        assert error_dict['error']['message'] == "Test validation error"
        assert 'timestamp' in error_dict['error']
        assert error_dict['error']['details']['field'] == "email"

    def test_error_code_status_mapping(self):
        """Test that error codes map to correct HTTP status codes"""
        from neet_app.error_codes import get_status_code
        
        assert get_status_code(ErrorCodes.AUTH_REQUIRED) == 401
        assert get_status_code(ErrorCodes.AUTH_FORBIDDEN) == 403
        assert get_status_code(ErrorCodes.NOT_FOUND) == 404
        assert get_status_code(ErrorCodes.INVALID_INPUT) == 400
        assert get_status_code(ErrorCodes.SERVER_ERROR) == 500
        assert get_status_code(ErrorCodes.RATE_LIMITED) == 429

    def test_timestamp_format(self, api_client):
        """Test that timestamps are in ISO format"""
        response = api_client.get('/api/chat-sessions/')
        
        assert response.status_code == 401
        error = response.json()['error']
        timestamp = error['timestamp']
        
        # Verify ISO format (should not raise exception)
        from datetime import datetime
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert parsed_timestamp is not None

    def test_error_details_in_debug_mode(self, api_client, settings):
        """Test that error details are included in debug mode"""
        settings.DEBUG = True
        
        # This test would require a view that includes debug details
        # For now, we'll test the concept with AppError
        app_error = AppError(
            code=ErrorCodes.SERVER_ERROR,
            message="Internal error",
            details={"debug_info": "Database query failed"}
        )
        
        error_dict = app_error.to_dict()
        assert error_dict['error']['details'] is not None

    def test_no_error_details_in_production(self, api_client, settings):
        """Test that sensitive error details are hidden in production"""
        settings.DEBUG = False
        
        # In production, sensitive details should be filtered out
        # This would be handled by the exception handler
        app_error = AppError(
            code=ErrorCodes.SERVER_ERROR,
            message="Internal error"
        )
        
        error_dict = app_error.to_dict()
        # Details should be None when not provided
        assert error_dict['error']['details'] is None


@pytest.mark.django_db
class TestErrorHandlerIntegration:
    """Integration tests for the error handling system"""

    def test_login_with_invalid_credentials(self, api_client, sample_student_profile):
        """Test login error handling"""
        response = api_client.post('/api/auth/login/', {
            'username': sample_student_profile.email,
            'password': 'wrong-password'
        })
        
        assert response.status_code == 401
        error = response.json()['error']
        assert error['code'] == ErrorCodes.AUTH_INVALID_CREDENTIALS
        assert 'Invalid credentials' in error['message']

    def test_login_with_missing_fields(self, api_client):
        """Test login validation error handling"""
        response = api_client.post('/api/auth/login/', {
            'username': 'test@example.com'
            # missing password
        })
        
        assert response.status_code == 400
        error = response.json()['error']
        assert error['code'] == ErrorCodes.INVALID_INPUT

    def test_password_reset_flow_errors(self, api_client):
        """Test password reset error handling"""
        # Test invalid email format
        response = api_client.post('/api/auth/forgot-password/', {
            'email': 'invalid-email'
        })
        
        # Should still return success to prevent enumeration
        assert response.status_code == 200

        # Test invalid token verification
        response = api_client.get('/api/auth/verify-reset-token/', {
            'email': 'test@example.com',
            'token': 'invalid'
        })
        
        assert response.status_code == 401
        error = response.json()['error']
        assert error['code'] == ErrorCodes.AUTH_TOKEN_INVALID

    def test_protected_endpoint_without_auth(self, api_client):
        """Test accessing protected endpoints without authentication"""
        protected_endpoints = [
            '/api/test-sessions/',
            '/api/student-profile/',
            '/api/chat-sessions/',
        ]
        
        for endpoint in protected_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == 401
            error = response.json()['error']
            assert error['code'] in [ErrorCodes.AUTH_REQUIRED, ErrorCodes.AUTH_TOKEN_INVALID]


# Fixtures for tests
@pytest.fixture
def sample_student_profile():
    """Create a sample student profile for testing"""
    from datetime import date
    student = StudentProfile.objects.create(
        student_id="TEST001",
        email="test@example.com",
        full_name="Test Student",
        date_of_birth=date(2000, 1, 1)  # Add required date_of_birth field
    )
    student.set_password("testpass123")
    student.save()
    return student


@pytest.fixture
def authenticated_student(sample_student_profile):
    """Create an authenticated student user for testing"""
    return sample_student_profile


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    return APIClient()

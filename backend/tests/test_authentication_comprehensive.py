"""
Unit tests for authentication functionality
Tests JWT authentication, Google OAuth, and permission systems
"""
import pytest
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken

from neet_app.models import StudentProfile


@pytest.mark.auth
@pytest.mark.unit
class TestStudentJWTAuthentication:
    """Test JWT authentication for students"""

    @pytest.mark.django_db
    def test_valid_jwt_token_authentication(self, api_client, sample_student_profile):
        """Test authentication with valid JWT token"""
        # Arrange - create a token tied to the actual user object
        refresh = RefreshToken.for_user(sample_student_profile)
        access_token = str(refresh.access_token)
        
        # Act
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/chat-sessions/')
        
        # Assert
        assert response.status_code in [200, 204]  # Success or empty list
        
        # Clean up
        api_client.credentials()

    @pytest.mark.django_db
    def test_invalid_jwt_token_authentication(self, api_client):
        """Test authentication with invalid JWT token"""
        # Arrange
        invalid_token = 'invalid.jwt.token'
        
        # Act
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {invalid_token}')
        response = api_client.get('/api/chat-sessions/')
        
        # Assert
        assert response.status_code == 401
        
        # Clean up
        api_client.credentials()

    @pytest.mark.django_db
    def test_expired_jwt_token_authentication(self, api_client, sample_student_profile):
        """Test authentication with expired JWT token"""
        # Arrange - create a token tied to the actual user object
        refresh = RefreshToken.for_user(sample_student_profile)
        access_token = str(refresh.access_token)
        
        # Mock the token to be expired
        from rest_framework_simplejwt.exceptions import InvalidToken
        with patch('rest_framework_simplejwt.authentication.JWTAuthentication.get_validated_token') as mock_validate:
            mock_validate.side_effect = InvalidToken("Token is invalid or expired")
            
            # Act
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            response = api_client.get('/api/chat-sessions/')
            
            # Assert
            assert response.status_code == 401
            
            # Clean up
            api_client.credentials()

    @pytest.mark.django_db
    def test_missing_authorization_header(self, api_client):
        """Test request without authorization header"""
        # Act
        response = api_client.get('/api/chat-sessions/')
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_malformed_authorization_header(self, api_client):
        """Test request with malformed authorization header"""
        # Arrange
        malformed_headers = [
            'Bearer',  # Missing token
            'InvalidScheme token123',  # Wrong scheme
            'Bearer token1 token2',  # Multiple tokens
        ]
        
        for header in malformed_headers:
            # Act
            api_client.credentials(HTTP_AUTHORIZATION=header)
            response = api_client.get('/api/chat-sessions/')
            
            # Assert
            assert response.status_code == 401

        # Clear credentials after test
        api_client.credentials()


@pytest.mark.auth
@pytest.mark.unit
class TestStudentLogin:
    """Test student login functionality"""

    @pytest.mark.django_db
    def test_valid_student_login(self, api_client, sample_student_profile):
        """Test successful student login"""
        # Arrange - ensure fixture has a known password for login
        known_password = 'studentpass123'
        sample_student_profile.set_password(known_password)
        sample_student_profile.save()
        
        login_data = {
            'username': sample_student_profile.student_id,  # Use student_id as username
            'password': known_password
        }
        
        # Act
        response = api_client.post('/api/auth/login/', login_data, format='json')
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert 'access' in response_data
        assert 'refresh' in response_data

    @pytest.mark.django_db
    def test_invalid_credentials_login(self, api_client, sample_student_profile):
        """Test login with invalid credentials"""
        # Arrange - ensure password is set to something different than wrongpassword
        sample_student_profile.set_password('correctpass')
        sample_student_profile.save()
        
        login_data = {
            'username': sample_student_profile.student_id,  # Use student_id as username
            'password': 'wrongpassword'
        }
        
        # Act
        response = api_client.post('/api/auth/login/', login_data, format='json')
        
        # Assert
        assert response.status_code in [400, 401]  # API returns 400 for invalid credentials

    @pytest.mark.django_db
    def test_nonexistent_user_login(self, api_client):
        """Test login with non-existent user"""
        # Arrange
        login_data = {
            'username': 'nonexistentuser',
            'password': 'somepassword'
        }
        
        # Act
        response = api_client.post('/api/auth/login/', login_data, format='json')
        
        # Assert
        assert response.status_code in [400, 401]  # API returns 400 for nonexistent user

    @pytest.mark.django_db
    def test_missing_credentials_login(self, api_client):
        """Test login with missing credentials"""
        # Test missing username
        response = api_client.post('/api/auth/login/', {'password': 'somepass'}, format='json')
        assert response.status_code == 400
        
        # Test missing password
        response = api_client.post('/api/auth/login/', {'username': 'someuser'}, format='json')
        assert response.status_code == 400
        
        # Test empty payload
        response = api_client.post('/api/auth/login/', {}, format='json')
        assert response.status_code == 400


@pytest.mark.auth
@pytest.mark.unit
class TestGoogleAuthentication:
    """Test Google OAuth authentication"""

    @pytest.mark.django_db
    @patch('neet_app.views.google_auth_views.verify_google_token')
    def test_successful_google_auth(self, mock_verify, api_client):
        """Test successful Google OAuth authentication"""
        # Arrange
        mock_verify.return_value = {
            'sub': 'google_user_id_123',
            'email': 'user@gmail.com',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg'
        }
        
        auth_data = {
            'idToken': 'valid_google_token'
        }
        
        # Act
        response = api_client.post('/api/auth/google/', auth_data, format='json')
        
        # Assert
        assert response.status_code in [200, 201]  # Success or created
        response_data = response.json()
        assert 'access' in response_data
        assert 'refresh' in response_data

    @pytest.mark.django_db
    @patch('neet_app.views.google_auth_views.verify_google_token')
    def test_invalid_google_token(self, mock_verify, api_client):
        """Test Google OAuth with invalid token"""
        # Arrange
        mock_verify.return_value = None  # verify_google_token returns None for invalid tokens
        
        auth_data = {
            'idToken': 'invalid_google_token'
        }
        
        # Act
        response = api_client.post('/api/auth/google/', auth_data, format='json')
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_missing_google_token(self, api_client):
        """Test Google OAuth with missing token"""
        # Act
        response = api_client.post('/api/auth/google/', {}, format='json')
        
        # Assert
        assert response.status_code == 400


@pytest.mark.auth
@pytest.mark.unit
class TestPermissions:
    """Test permission system for different endpoints"""

    @pytest.mark.django_db
    def test_protected_endpoints_require_authentication(self, api_client):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            '/api/chat-sessions/',
            '/api/test-sessions/',
            '/api/student-profile/',
            '/api/insights/student/',
        ]
        
        for endpoint in protected_endpoints:
            # Act
            response = api_client.get(endpoint)
            
            # Assert - expect 401 (unauthenticated) or 403 (forbidden based on implementation)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"

    @pytest.mark.django_db
    def test_student_can_only_access_own_data(self, api_client):
        """Test that students can only access their own data"""
        # Arrange - create two students
        profile1 = StudentProfile.objects.create(
            student_id='STU25010100001', full_name='Student 1', email='s1@test.com',
            date_of_birth='2000-01-01'
        )
        profile1.set_password('pass')
        profile1.save()
        
        profile2 = StudentProfile.objects.create(
            student_id='STU25010100002', full_name='Student 2', email='s2@test.com',
            date_of_birth='2000-01-02'
        )
        profile2.set_password('pass')
        profile2.save()
        
        # Authenticate as student1 - use proper token creation
        refresh = RefreshToken.for_user(profile1)
        access_token = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Act - try to access student2's profile
        response = api_client.get(f'/api/students/{profile2.student_id}/')
        
        # Assert - should be forbidden or not found depending on implementation
        assert response.status_code in [403, 404], "Students should not be able to access other students' private data"
        
        # Clean up
        api_client.credentials()


@pytest.mark.auth 
@pytest.mark.unit
class TestPasswordReset:
    """Test password reset functionality"""

    @pytest.mark.django_db
    def test_forgot_password_valid_email(self, api_client, sample_student_profile):
        """Test forgot password with valid email"""
        # Arrange
        reset_data = {
            'email': sample_student_profile.email
        }
        
        # Act
        response = api_client.post('/api/auth/forgot-password/', reset_data, format='json')
        
        # Assert
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_forgot_password_invalid_email(self, api_client):
        """Test forgot password with invalid email"""
        # Arrange
        reset_data = {
            'email': 'nonexistent@example.com'
        }
        
        # Act
        response = api_client.post('/api/auth/forgot-password/', reset_data, format='json')
        
        # Assert - some APIs return 200 for security (don't disclose if email exists)
        assert response.status_code in [200, 400, 404]

    @pytest.mark.django_db
    def test_forgot_password_missing_email(self, api_client):
        """Test forgot password with missing email"""
        # Act
        response = api_client.post('/api/auth/forgot-password/', {}, format='json')
        
        # Assert
        assert response.status_code == 400

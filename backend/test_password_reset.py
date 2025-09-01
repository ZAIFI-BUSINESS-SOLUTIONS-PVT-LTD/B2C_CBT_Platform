from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from .neet_app.models import StudentProfile, PasswordReset


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = StudentProfile.objects.create(
            student_id='STU0001',
            full_name='Test User',
            email='test@example.com',
            date_of_birth='2000-01-01',
            password_hash='pbkdf2_sha256$dummy'
        )

    def test_forgot_password_creates_token(self):
        url = '/api/auth/forgot-password/'
        resp = self.client.post(url, {'email': 'test@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        # Ensure a PasswordReset record exists
        prs = PasswordReset.objects.filter(user=self.user)
        self.assertTrue(prs.exists())

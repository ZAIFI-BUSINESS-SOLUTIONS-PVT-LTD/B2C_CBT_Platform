import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta

from neet_app.models import StudentProfile, RazorpayOrder
from neet_app.services.razorpay_service import create_order, verify_payment_signature


class PaymentViewsTestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.student = StudentProfile.objects.create(
            student_id='TEST001',
            email='test@example.com',
            name='Test Student'
        )
        self.client.force_authenticate(user=self.student)
        
        # URLs
        self.create_order_url = reverse('create-order')
        self.verify_payment_url = reverse('verify-payment')
        self.subscription_status_url = reverse('subscription-status')

    @patch('neet_app.views.payment_views.create_order')
    def test_create_order_success(self, mock_create_order):
        """Test successful order creation"""
        # Mock Razorpay response
        mock_create_order.return_value = {
            'id': 'order_test123',
            'currency': 'INR',
            'amount': 150000
        }
        
        data = {'plan': 'basic'}
        response = self.client.post(self.create_order_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_id', response.data)
        self.assertIn('local_order_id', response.data)
        self.assertEqual(response.data['plan'], 'basic')
        self.assertEqual(response.data['amount'], 150000)
        
        # Verify order was created in database
        order = RazorpayOrder.objects.get(id=response.data['local_order_id'])
        self.assertEqual(order.student, self.student)
        self.assertEqual(order.plan, 'basic')
        self.assertEqual(order.status, 'created')

    @patch('neet_app.views.payment_views.create_order')
    def test_create_order_razorpay_failure(self, mock_create_order):
        """Test order creation when Razorpay API fails"""
        # Mock Razorpay API failure
        mock_create_order.side_effect = Exception("Razorpay API Error")
        
        data = {'plan': 'pro'}
        response = self.client.post(self.create_order_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('error', response.data)
        
        # Verify local order was still created with remote_failed status
        self.assertTrue(RazorpayOrder.objects.filter(
            student=self.student, 
            status='remote_failed'
        ).exists())

    def test_create_order_invalid_plan(self):
        """Test order creation with invalid plan"""
        data = {'plan': 'invalid_plan'}
        response = self.client.post(self.create_order_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_create_order_missing_plan(self):
        """Test order creation without plan"""
        data = {}
        response = self.client.post(self.create_order_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('neet_app.views.payment_views.verify_payment_signature')
    def test_verify_payment_success(self, mock_verify):
        """Test successful payment verification"""
        # Create a test order
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            razorpay_order_id='order_test123',
            status='created'
        )
        
        # Mock signature verification success
        mock_verify.return_value = True
        
        data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123',
            'local_order_id': order.id
        }
        
        response = self.client.post(self.verify_payment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['plan'], 'basic')
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'pay_test123')
        
        # Verify student subscription updated
        self.student.refresh_from_db()
        self.assertEqual(self.student.subscription_plan, 'basic')
        self.assertIsNotNone(self.student.subscription_expires_at)

    @patch('neet_app.views.payment_views.verify_payment_signature')
    def test_verify_payment_invalid_signature(self, mock_verify):
        """Test payment verification with invalid signature"""
        # Create a test order
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            razorpay_order_id='order_test123',
            status='created'
        )
        
        # Mock signature verification failure
        mock_verify.return_value = False
        
        data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'invalid_signature',
            'local_order_id': order.id
        }
        
        response = self.client.post(self.verify_payment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Verify order status updated to failed
        order.refresh_from_db()
        self.assertEqual(order.status, 'failed')
        
        # Verify student subscription not updated
        self.student.refresh_from_db()
        self.assertIsNone(self.student.subscription_plan)

    @patch('neet_app.views.payment_views.verify_payment_signature')
    def test_verify_payment_idempotent(self, mock_verify):
        """Test that verify payment is idempotent"""
        # Create a test order that's already paid
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            razorpay_order_id='order_test123',
            razorpay_payment_id='pay_test123',
            status='paid'
        )
        
        data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123',
            'local_order_id': order.id
        }
        
        response = self.client.post(self.verify_payment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'already_paid')
        
        # Verify signature verification was not called
        mock_verify.assert_not_called()

    def test_verify_payment_order_not_found(self):
        """Test payment verification for non-existent order"""
        data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123',
            'local_order_id': 99999  # Non-existent order
        }
        
        response = self.client.post(self.verify_payment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_payment_order_id_mismatch(self):
        """Test payment verification with mismatched order ID"""
        # Create a test order
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            razorpay_order_id='order_test123',
            status='created'
        )
        
        data = {
            'razorpay_order_id': 'order_different',  # Different order ID
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123',
            'local_order_id': order.id
        }
        
        response = self.client.post(self.verify_payment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Order ID mismatch', response.data['error'])

    def test_subscription_status_active(self):
        """Test subscription status for active subscription"""
        # Set up active subscription
        future_date = timezone.now() + timedelta(days=15)
        self.student.subscription_plan = 'pro'
        self.student.subscription_expires_at = future_date
        self.student.save()
        
        response = self.client.get(self.subscription_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subscription_plan'], 'pro')
        self.assertTrue(response.data['is_active'])
        self.assertIn('available_plans', response.data)

    def test_subscription_status_expired(self):
        """Test subscription status for expired subscription"""
        # Set up expired subscription
        past_date = timezone.now() - timedelta(days=1)
        self.student.subscription_plan = 'basic'
        self.student.subscription_expires_at = past_date
        self.student.save()
        
        response = self.client.get(self.subscription_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subscription_plan'], 'basic')
        self.assertFalse(response.data['is_active'])

    def test_subscription_status_no_subscription(self):
        """Test subscription status for user with no subscription"""
        response = self.client.get(self.subscription_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['subscription_plan'])
        self.assertFalse(response.data['is_active'])

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access payment endpoints"""
        self.client.force_authenticate(user=None)
        
        # Test create order
        response = self.client.post(self.create_order_url, {'plan': 'basic'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test verify payment
        response = self.client.post(self.verify_payment_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test subscription status
        response = self.client.get(self.subscription_status_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RazorpayServiceTestCase(TestCase):
    """Test the Razorpay service functions"""
    
    @patch('neet_app.services.razorpay_service.get_client')
    def test_create_order_success(self, mock_get_client):
        """Test successful order creation via service"""
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            'id': 'order_test123',
            'amount': 150000,
            'currency': 'INR'
        }
        mock_get_client.return_value = mock_client
        
        result = create_order(150000, 'INR', 'test_receipt')
        
        self.assertEqual(result['id'], 'order_test123')
        mock_client.order.create.assert_called_once_with({
            'amount': 150000,
            'currency': 'INR',
            'receipt': 'test_receipt'
        })

    @patch('neet_app.services.razorpay_service.get_client')
    def test_create_order_failure(self, mock_get_client):
        """Test order creation failure"""
        mock_client = MagicMock()
        mock_client.order.create.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client
        
        with self.assertRaises(Exception):
            create_order(150000, 'INR')

    @patch('neet_app.services.razorpay_service.get_client')
    def test_verify_payment_signature_success(self, mock_get_client):
        """Test successful signature verification"""
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = None  # No exception = success
        mock_get_client.return_value = mock_client
        
        payload = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123'
        }
        
        result = verify_payment_signature(payload)
        
        self.assertTrue(result)
        mock_client.utility.verify_payment_signature.assert_called_once()

    @patch('neet_app.services.razorpay_service.get_client')
    def test_verify_payment_signature_failure(self, mock_get_client):
        """Test signature verification failure"""
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.side_effect = Exception("Invalid signature")
        mock_get_client.return_value = mock_client
        
        payload = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'invalid_signature'
        }
        
        result = verify_payment_signature(payload)
        
        self.assertFalse(result)


class RazorpayOrderModelTestCase(TestCase):
    """Test the RazorpayOrder model"""
    
    def setUp(self):
        self.student = StudentProfile.objects.create(
            student_id='TEST001',
            email='test@example.com',
            name='Test Student'
        )

    def test_mark_paid(self):
        """Test the mark_paid method"""
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            razorpay_order_id='order_test123',
            status='created'
        )
        
        order.mark_paid('pay_test123', 'signature_test123')
        
        self.assertEqual(order.razorpay_payment_id, 'pay_test123')
        self.assertEqual(order.razorpay_signature, 'signature_test123')
        self.assertEqual(order.status, 'paid')

    def test_string_representation(self):
        """Test string representation of the model"""
        order = RazorpayOrder.objects.create(
            student=self.student,
            plan='basic',
            amount=150000,
            currency='INR',
            status='created'
        )
        
        # Test that the string representation doesn't raise an error
        str_repr = str(order)
        self.assertIsInstance(str_repr, str)
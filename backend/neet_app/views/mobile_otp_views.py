"""
Mobile OTP Authentication Views
Handles send-otp and verify-otp endpoints for mobile-based login
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction

from ..models import StudentProfile
from ..serializers import StudentProfileSerializer
from ..authentication import StudentUser, StudentTokenObtainPairSerializer
from ..utils.otp import (
    normalize_mobile, validate_mobile, generate_otp, 
    redis_set_otp, redis_get_otp_hash, redis_delete_otp, verify_otp_hash,
    increment_attempts, check_rate_limit, set_cooldown, check_cooldown
)
from ..utils.sms import send_otp_sms
from ..utils.student_utils import generate_unique_student_id_for_mobile
from ..errors import ValidationError, AuthenticationError
from ..error_codes import ErrorCodes

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send OTP to mobile number
    
    Request body:
    {
        "mobile_number": "9876543210" or "+919876543210"
    }
    
    Response:
    200: {"message": "OTP sent successfully", "cooldown_seconds": 30}
    400: {"detail": "Invalid mobile number format"}
    429: {"detail": "Rate limit exceeded" or "Please wait before requesting another OTP"}
    502: {"detail": "SMS service temporarily unavailable"}
    """
    try:
        mobile_input = request.data.get('mobile_number')
        
        if not mobile_input:
            return Response({
                'detail': 'Mobile number is required',
                'code': ErrorCodes.VALIDATION_ERROR
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize and validate mobile number
        mobile = normalize_mobile(mobile_input)
        if not mobile or not validate_mobile(mobile):
            return Response({
                'detail': 'Invalid mobile number format. Please enter a valid Indian mobile number.',
                'code': ErrorCodes.VALIDATION_ERROR
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check rate limit
        is_rate_limited, current_count, max_allowed = check_rate_limit(mobile)
        if is_rate_limited:
            return Response({
                'detail': f'Too many OTP requests. Maximum {max_allowed} requests per hour allowed.',
                'code': ErrorCodes.RATE_LIMIT_EXCEEDED,
                'retry_after': 3600  # 1 hour in seconds
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Check cooldown
        is_in_cooldown, remaining_seconds = check_cooldown(mobile)
        if is_in_cooldown:
            return Response({
                'detail': f'Please wait {remaining_seconds} seconds before requesting another OTP.',
                'code': ErrorCodes.RATE_LIMIT_EXCEEDED,
                'cooldown_seconds': remaining_seconds
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP in Redis
        if not redis_set_otp(mobile, otp):
            logger.error(f"Failed to store OTP in Redis for {mobile}")
            return Response({
                'detail': 'Unable to process OTP request. Please try again.',
                'code': ErrorCodes.SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Increment attempts counter (for rate limiting)
        increment_attempts(mobile)
        
        # Set cooldown
        set_cooldown(mobile)
        
        # Send OTP via SMS
        sms_result = send_otp_sms(mobile, otp)
        
        if not sms_result['success']:
            # If SMS fails, we should clean up the stored OTP
            redis_delete_otp(mobile)
            
            logger.error(f"SMS sending failed for {mobile}: {sms_result['error']}")
            
            return Response({
                'detail': 'SMS service temporarily unavailable. Please try again later.',
                'code': ErrorCodes.SMS_SERVICE_ERROR,
                'technical_error': sms_result['error']
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        logger.info(f"OTP sent successfully to {mobile}, MessageId: {sms_result.get('message_id')}")
        
        return Response({
            'message': 'OTP sent successfully to your mobile number.',
            'cooldown_seconds': 30,
            'expires_in': 300  # 5 minutes
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Unexpected error in send_otp for {mobile_input}: {str(e)}")
        return Response({
            'detail': 'An unexpected error occurred. Please try again.',
            'code': ErrorCodes.SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





def convert_to_camel_case(student_data):
    """
    Convert snake_case keys to camelCase for frontend consistency
    Replicates the logic from authentication.py
    """
    camel_case_student = {}
    for key, value in student_data.items():
        if '_' in key:
            parts = key.split('_')
            camel_key = parts[0] + ''.join(word.capitalize() for word in parts[1:])
            camel_case_student[camel_key] = value
        else:
            camel_case_student[key] = value
    
    return camel_case_student


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP and authenticate user
    
    Request body:
    {
        "mobile_number": "+919876543210",
        "otp_code": "123456"
    }
    
    Response:
    200: {"access": "...", "refresh": "...", "student": {...}}
    400: {"detail": "Invalid or expired OTP"}
    """
    try:
        mobile_input = request.data.get('mobile_number')
        otp_code = request.data.get('otp_code')
        
        if not mobile_input or not otp_code:
            return Response({
                'detail': 'Mobile number and OTP code are required',
                'code': ErrorCodes.VALIDATION_ERROR
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize mobile number
        mobile = normalize_mobile(mobile_input)
        if not mobile or not validate_mobile(mobile):
            return Response({
                'detail': 'Invalid mobile number format',
                'code': ErrorCodes.VALIDATION_ERROR
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate OTP format
        if not otp_code.isdigit() or len(otp_code) != 6:
            return Response({
                'detail': 'OTP must be a 6-digit number',
                'code': ErrorCodes.VALIDATION_ERROR
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get stored OTP hash from Redis
        stored_otp_hash = redis_get_otp_hash(mobile)
        if not stored_otp_hash:
            return Response({
                'detail': 'OTP has expired or is invalid. Please request a new OTP.',
                'code': ErrorCodes.OTP_EXPIRED
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify OTP
        if not verify_otp_hash(otp_code, stored_otp_hash):
            return Response({
                'detail': 'Invalid OTP. Please check and try again.',
                'code': ErrorCodes.OTP_INVALID
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # OTP is valid, delete it (one-time use)
        redis_delete_otp(mobile)
        
        # Find or create student profile
        student = None
        created = False
        
        try:
            student = StudentProfile.objects.get(phone_number=mobile)
            logger.info(f"Found existing student profile for {mobile}: {student.student_id}")
        except StudentProfile.DoesNotExist:
            # Auto-create minimal student profile
            try:
                with transaction.atomic():
                    student_id = generate_unique_student_id_for_mobile(mobile)
                    
                    student = StudentProfile.objects.create(
                        student_id=student_id,
                        phone_number=mobile,
                        is_active=True,
                        is_verified=True,  # Mobile verification complete
                        auth_provider='mobile',
                        # Leave email, date_of_birth, full_name as null for later completion
                    )
                    created = True
                    logger.info(f"Created new mobile-only student profile: {student.student_id}")
                    
            except Exception as e:
                logger.error(f"Failed to create student profile for {mobile}: {str(e)}")
                return Response({
                    'detail': 'Unable to create account. Please try again.',
                    'code': ErrorCodes.SERVER_ERROR
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Generate JWT tokens using existing authentication logic
        try:
            # Create StudentUser wrapper (required by existing token logic)
            student_user = StudentUser(student)
            
            # Generate tokens using existing serializer logic
            refresh = StudentTokenObtainPairSerializer.get_token(student_user)
            
            # Add custom claims
            refresh['student_id'] = student.student_id
            refresh['email'] = student.email  # May be None for mobile-only accounts
            
            # Generate token strings
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last login
            student.last_login = timezone.now()
            student.save(update_fields=['last_login'])
            
            # Create or update StudentActivity for admin dashboard
            try:
                from ..models import StudentActivity
                now = timezone.now()
                StudentActivity.objects.update_or_create(
                    student=student,
                    defaults={
                        'last_seen': now,
                        'ip_address': request.META.get('REMOTE_ADDR'),
                        'user_agent': request.META.get('HTTP_USER_AGENT')
                    }
                )
            except Exception as activity_error:
                # Non-fatal; don't block login
                logger.warning(f"Failed to update StudentActivity: {activity_error}")
            
            # Serialize student profile
            student_data = StudentProfileSerializer(student).data
            
            # Convert to camelCase for frontend consistency
            camel_case_student = convert_to_camel_case(student_data)
            
            # Add profile completion flag
            camel_case_student['isProfileComplete'] = bool(
                student.email and student.date_of_birth and student.full_name
            )
            camel_case_student['isNewUser'] = created
            
            logger.info(f"OTP verification successful for {mobile}, student_id: {student.student_id}")
            
            return Response({
                'access': access_token,
                'refresh': refresh_token,
                'student': camel_case_student,
                'message': 'Login successful' if not created else 'Account created and login successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as token_error:
            logger.error(f"Token generation failed for {mobile}: {str(token_error)}")
            return Response({
                'detail': 'Authentication successful but token generation failed. Please try again.',
                'code': ErrorCodes.SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.exception(f"Unexpected error in verify_otp for {mobile_input}: {str(e)}")
        return Response({
            'detail': 'An unexpected error occurred. Please try again.',
            'code': ErrorCodes.SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
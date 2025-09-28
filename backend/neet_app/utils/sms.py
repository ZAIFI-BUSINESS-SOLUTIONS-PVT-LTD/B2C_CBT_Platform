"""
SMS sending utilities using AWS SNS with DLT compliance
"""
import boto3
import logging
import time
from django.conf import settings
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)

# AWS Configuration
AWS_ACCESS_KEY_ID = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
AWS_REGION = getattr(settings, 'AWS_REGION', 'ap-south-1')
SNS_SENDER_ID = getattr(settings, 'SNS_SENDER_ID', 'NEET')
APP_NAME = getattr(settings, 'APP_NAME', 'NeetNinja')

def get_sns_client():
    """
    Create and return AWS SNS client
    """
    try:
        client = boto3.client(
            'sns',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create SNS client: {e}")
        raise Exception(f"SNS client creation failed: {e}")

def format_otp_message(otp, app_name=None):
    """
    Format OTP message for SMS
    """
    if app_name is None:
        app_name = APP_NAME
    
    return f"Your OTP for {app_name} login is {otp}. Valid for 5 minutes. Do not share this OTP with anyone."

def send_sms_via_sns(mobile_number, message, max_retries=3):
    """
    Send SMS via AWS SNS with retry logic
    
    Args:
        mobile_number: E.164 format mobile number (+919876543210)
        message: SMS message content
        max_retries: Maximum number of retry attempts
    
    Returns:
        dict: Result with success status, message_id, and error info
    """
    result = {
        'success': False,
        'message_id': None,
        'error': None,
        'attempts': 0
    }
    
    if not mobile_number or not message:
        result['error'] = 'Mobile number and message are required'
        return result
    
    try:
        sns_client = get_sns_client()
    except Exception as e:
        result['error'] = f'SNS client initialization failed: {str(e)}'
        return result
    
    for attempt in range(max_retries):
        result['attempts'] = attempt + 1
        
        try:
            # Prepare message attributes for DLT compliance
            message_attributes = {
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': SNS_SENDER_ID
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
            
            # Send SMS
            response = sns_client.publish(
                PhoneNumber=mobile_number,
                Message=message,
                MessageAttributes=message_attributes
            )
            
            # Success
            result['success'] = True
            result['message_id'] = response.get('MessageId')
            
            logger.info(f"SMS sent successfully to {mobile_number}, MessageId: {result['message_id']}")
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.warning(f"SNS ClientError (attempt {attempt + 1}): {error_code} - {error_message}")
            
            # Check if error is retryable
            if error_code in ['Throttling', 'ServiceUnavailable', 'InternalError']:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(sleep_time)
                    continue
            
            result['error'] = f'SNS Error: {error_code} - {error_message}'
            break
            
        except BotoCoreError as e:
            logger.warning(f"SNS BotoCoreError (attempt {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff for network issues
                sleep_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(sleep_time)
                continue
            
            result['error'] = f'SNS Connection Error: {str(e)}'
            break
            
        except Exception as e:
            logger.error(f"Unexpected error sending SMS (attempt {attempt + 1}): {str(e)}")
            result['error'] = f'Unexpected error: {str(e)}'
            break
    
    if not result['success']:
        logger.error(f"Failed to send SMS to {mobile_number} after {result['attempts']} attempts: {result['error']}")
    
    return result

def send_otp_sms(mobile_number, otp):
    """
    Send OTP SMS to mobile number
    
    Args:
        mobile_number: E.164 format mobile number
        otp: 6-digit OTP code
    
    Returns:
        dict: Result with success status and details
    """
    message = format_otp_message(otp)
    
    logger.info(f"Sending OTP SMS to {mobile_number}")
    
    # Note: We log the send attempt but never log the actual OTP for security
    result = send_sms_via_sns(mobile_number, message)
    
    if result['success']:
        logger.info(f"OTP SMS sent successfully to {mobile_number}, MessageId: {result['message_id']}")
    else:
        logger.error(f"Failed to send OTP SMS to {mobile_number}: {result['error']}")
    
    return result
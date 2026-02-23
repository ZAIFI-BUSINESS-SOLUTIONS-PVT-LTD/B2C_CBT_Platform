"""
SMS sending utilities using MSG91 API
"""
import http.client
import json
import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)

# MSG91 Configuration
MSG91_AUTH_KEY = getattr(settings, 'MSG91_AUTH_KEY', None)
MSG91_TEMPLATE_ID = getattr(settings, 'MSG91_TEMPLATE_ID', None)
MSG91_OTP_EXPIRY = getattr(settings, 'MSG91_OTP_EXPIRY', '5')  # minutes
APP_NAME = getattr(settings, 'APP_NAME', 'NeetNinja')

def normalize_mobile_for_msg91(mobile_number):
    """
    Convert E.164 format (+919876543210) to MSG91 format (919876543210)
    MSG91 expects country code + number without the + prefix
    """
    if not mobile_number:
        return None
    
    # Remove + prefix if present
    mobile = mobile_number.strip()
    if mobile.startswith('+'):
        mobile = mobile[1:]
    
    return mobile

def send_sms_via_msg91(mobile_number, otp, max_retries=3):
    """
    Send OTP SMS via MSG91 API with retry logic
    
    Args:
        mobile_number: E.164 format mobile number (+919876543210)
        otp: 6-digit OTP code
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
    
    if not mobile_number or not otp:
        result['error'] = 'Mobile number and OTP are required'
        return result
    
    # Check if MSG91 credentials are configured
    if not MSG91_AUTH_KEY or not MSG91_TEMPLATE_ID:
        result['error'] = 'MSG91 credentials not configured. Set MSG91_AUTH_KEY and MSG91_TEMPLATE_ID in settings.'
        logger.error(result['error'])
        return result
    
    # Normalize mobile number for MSG91 (remove + prefix)
    mobile_normalized = normalize_mobile_for_msg91(mobile_number)
    if not mobile_normalized:
        result['error'] = 'Invalid mobile number format'
        return result
    
    for attempt in range(max_retries):
        result['attempts'] = attempt + 1
        
        try:
            # Create HTTPS connection to MSG91
            conn = http.client.HTTPSConnection("control.msg91.com", timeout=10)
            
            # Prepare request headers
            headers = {
                'content-type': "application/json",
                'Content-Type': "application/JSON"
            }
            
            # Build URL with query parameters
            # MSG91 OTP API sends the OTP automatically using the configured template
            url = (
                f"/api/v5/otp?"
                f"mobile={mobile_normalized}&"
                f"authkey={MSG91_AUTH_KEY}&"
                f"otp={otp}&"
                f"otp_expiry={MSG91_OTP_EXPIRY}&"
                f"template_id={MSG91_TEMPLATE_ID}&"
                f"realTimeResponse=1"
            )
            
            # Empty payload (MSG91 doesn't require body for OTP endpoint)
            payload = "{}"
            
            # Make the request
            conn.request("POST", url, payload, headers)
            
            # Get response
            res = conn.getresponse()
            data = res.read()
            response_text = data.decode("utf-8")
            
            # Close connection
            conn.close()
            
            # Parse JSON response
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse MSG91 response: {response_text}")
                result['error'] = f'Invalid JSON response from MSG91: {response_text}'
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + (0.1 * attempt)
                    time.sleep(sleep_time)
                    continue
                break
            
            # Check response status
            response_type = response_data.get('type')
            
            if response_type == 'success':
                # Success
                result['success'] = True
                result['message_id'] = response_data.get('request_id', 'msg91-success')
                logger.info(f"OTP sent successfully to {mobile_number} via MSG91, request_id: {result['message_id']}")
                return result
            else:
                # Error from MSG91
                error_message = response_data.get('message', 'Unknown error from MSG91')
                logger.warning(f"MSG91 Error (attempt {attempt + 1}): {error_message}")
                
                # Check if error is retryable (rate limit, server error, etc.)
                if 'rate limit' in error_message.lower() or 'server error' in error_message.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        sleep_time = (2 ** attempt) + (0.1 * attempt)
                        time.sleep(sleep_time)
                        continue
                
                result['error'] = f'MSG91 Error: {error_message}'
                break
            
        except http.client.HTTPException as e:
            logger.warning(f"MSG91 HTTPException (attempt {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff for network issues
                sleep_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(sleep_time)
                continue
            
            result['error'] = f'MSG91 Connection Error: {str(e)}'
            break
            
        except Exception as e:
            logger.error(f"Unexpected error sending SMS via MSG91 (attempt {attempt + 1}): {str(e)}")
            result['error'] = f'Unexpected error: {str(e)}'
            
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + (0.1 * attempt)
                time.sleep(sleep_time)
                continue
            break
    
    if not result['success']:
        logger.error(f"Failed to send SMS to {mobile_number} after {result['attempts']} attempts: {result['error']}")
    
    return result

def send_otp_sms(mobile_number, otp):
    """
    Send OTP SMS to mobile number using MSG91
    
    Args:
        mobile_number: E.164 format mobile number (+919876543210)
        otp: 6-digit OTP code
    
    Returns:
        dict: Result with success status and details
    """
    logger.info(f"Sending OTP SMS to {mobile_number} via MSG91")
    
    # Note: We log the send attempt but never log the actual OTP for security
    result = send_sms_via_msg91(mobile_number, otp)
    
    if result['success']:
        logger.info(f"OTP SMS sent successfully to {mobile_number}, request_id: {result['message_id']}")
    else:
        logger.error(f"Failed to send OTP SMS to {mobile_number}: {result['error']}")
    
    return result

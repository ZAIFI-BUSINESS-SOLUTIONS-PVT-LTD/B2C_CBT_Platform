"""
OTP generation, validation, and Redis storage utilities
"""
import secrets
import hmac
import hashlib
import re
import logging
from django.conf import settings
from .redis_client import get_redis

logger = logging.getLogger(__name__)

# Configuration constants with defaults
OTP_TTL_SECONDS = getattr(settings, 'OTP_TTL_SECONDS', 300)  # 5 minutes
OTP_RATE_LIMIT_PER_HOUR = getattr(settings, 'OTP_RATE_LIMIT_PER_HOUR', 5)
OTP_RESEND_COOLDOWN_SECONDS = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 30)
OTP_HASH_SECRET = getattr(settings, 'OTP_HASH_SECRET', 'default-otp-secret-change-in-production')

def normalize_mobile(mobile):
    """
    Normalize mobile number to E.164 format for India
    Input: various formats like 9876543210, +919876543210, etc.
    Output: +919876543210
    """
    if not mobile:
        return None
    
    # Remove all whitespace and special characters except +
    mobile = re.sub(r'[^\d+]', '', str(mobile))
    
    # Remove leading zeros
    mobile = mobile.lstrip('0')
    
    # If already has +91, validate and return
    if mobile.startswith('+91'):
        if len(mobile) == 13 and mobile[3:].isdigit():
            return mobile
        else:
            return None
    
    # If starts with 91, add +
    if mobile.startswith('91') and len(mobile) == 12:
        return '+' + mobile
    
    # If 10 digits, assume Indian number and add +91
    if len(mobile) == 10 and mobile.isdigit():
        return '+91' + mobile
    
    return None

def validate_mobile(mobile):
    """
    Validate if mobile number is in correct E.164 format for India
    """
    if not mobile:
        return False
    
    # Should be +91 followed by 10 digits
    pattern = r'^\+91[6-9]\d{9}$'
    return bool(re.match(pattern, mobile))

def generate_otp():
    """
    Generate a secure 6-digit OTP
    """
    return f"{secrets.randbelow(1000000):06d}"

def hash_otp(otp):
    """
    Create HMAC-SHA256 hash of OTP with secret
    """
    secret = OTP_HASH_SECRET.encode('utf-8')
    otp_bytes = str(otp).encode('utf-8')
    return hmac.new(secret, otp_bytes, hashlib.sha256).hexdigest()

def verify_otp_hash(otp, stored_hash):
    """
    Verify OTP against stored hash in constant time
    """
    computed_hash = hash_otp(otp)
    return hmac.compare_digest(computed_hash, stored_hash)

def redis_set_otp(mobile, otp, ttl_seconds=None):
    """
    Store OTP hash in Redis with TTL
    """
    if ttl_seconds is None:
        ttl_seconds = OTP_TTL_SECONDS
    
    try:
        redis = get_redis()
        otp_hash = hash_otp(otp)
        key = f"otp:{mobile}"
        redis.setex(key, ttl_seconds, otp_hash)
        logger.info(f"OTP stored for mobile {mobile} with TTL {ttl_seconds}s")
        return True
    except Exception as e:
        logger.error(f"Failed to store OTP in Redis for {mobile}: {e}")
        return False

def redis_get_otp_hash(mobile):
    """
    Get OTP hash from Redis
    """
    try:
        redis = get_redis()
        key = f"otp:{mobile}"
        return redis.get(key)
    except Exception as e:
        logger.error(f"Failed to get OTP from Redis for {mobile}: {e}")
        return None

def redis_delete_otp(mobile):
    """
    Delete OTP from Redis (one-time use)
    """
    try:
        redis = get_redis()
        key = f"otp:{mobile}"
        return redis.delete(key) > 0
    except Exception as e:
        logger.error(f"Failed to delete OTP from Redis for {mobile}: {e}")
        return False

def increment_attempts(mobile):
    """
    Increment and return current attempt count for rate limiting
    Returns current count after increment
    """
    try:
        redis = get_redis()
        key = f"otp_attempts:{mobile}"
        
        # Use pipeline for atomic operations
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)  # 1 hour TTL
        results = pipe.execute()
        
        current_count = results[0]
        logger.info(f"OTP attempts for {mobile}: {current_count}")
        return current_count
    except Exception as e:
        logger.error(f"Failed to increment attempts for {mobile}: {e}")
        return 0

def get_attempts_count(mobile):
    """
    Get current attempt count without incrementing
    """
    try:
        redis = get_redis()
        key = f"otp_attempts:{mobile}"
        count = redis.get(key)
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"Failed to get attempts count for {mobile}: {e}")
        return 0

def set_cooldown(mobile, seconds=None):
    """
    Set resend cooldown for mobile number
    """
    if seconds is None:
        seconds = OTP_RESEND_COOLDOWN_SECONDS
    
    try:
        redis = get_redis()
        key = f"otp_cooldown:{mobile}"
        redis.setex(key, seconds, "1")
        logger.info(f"Cooldown set for {mobile} for {seconds}s")
        return True
    except Exception as e:
        logger.error(f"Failed to set cooldown for {mobile}: {e}")
        return False

def get_cooldown_remaining(mobile):
    """
    Get remaining cooldown time in seconds
    Returns 0 if no cooldown active
    """
    try:
        redis = get_redis()
        key = f"otp_cooldown:{mobile}"
        ttl = redis.ttl(key)
        return max(0, ttl) if ttl > 0 else 0
    except Exception as e:
        logger.error(f"Failed to get cooldown for {mobile}: {e}")
        return 0

def check_rate_limit(mobile):
    """
    Check if mobile number has exceeded rate limit
    Returns tuple: (is_rate_limited, current_count, max_allowed)
    """
    current_count = get_attempts_count(mobile)
    is_limited = current_count >= OTP_RATE_LIMIT_PER_HOUR
    return is_limited, current_count, OTP_RATE_LIMIT_PER_HOUR

def check_cooldown(mobile):
    """
    Check if mobile number is in cooldown period
    Returns tuple: (is_in_cooldown, remaining_seconds)
    """
    remaining = get_cooldown_remaining(mobile)
    return remaining > 0, remaining
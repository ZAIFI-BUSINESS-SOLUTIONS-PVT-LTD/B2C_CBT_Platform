"""
Redis client configuration for OTP and caching functionality
"""
import redis
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_redis_client():
    """
    Get Redis client instance with connection pooling
    """
    try:
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        # Test connection
        client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise Exception(f"Redis connection failed: {e}")

# Global Redis client instance
redis_client = None

def get_redis():
    """
    Get or create Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_client = get_redis_client()
    return redis_client
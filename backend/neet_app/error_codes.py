"""
Centralized error codes for the NEET Practice Platform.

This module defines all standardized error codes used throughout the application.
Each error code should be descriptive and mapped to appropriate HTTP status codes.
"""

class ErrorCodes:
    """
    Centralized error code definitions.
    
    Format: ERROR_CATEGORY_SPECIFIC_ISSUE
    """
    
    # Authentication & Authorization Errors (400-403)
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    AUTH_GOOGLE_TOKEN_INVALID = "AUTH_GOOGLE_TOKEN_INVALID"
    
    # Input Validation Errors (400)
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_EMAIL_FORMAT = "INVALID_EMAIL_FORMAT"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    INVALID_STUDENT_ID = "INVALID_STUDENT_ID"
    
    # Resource Errors (404)
    NOT_FOUND = "NOT_FOUND"
    STUDENT_NOT_FOUND = "STUDENT_NOT_FOUND"
    TEST_SESSION_NOT_FOUND = "TEST_SESSION_NOT_FOUND"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    CHAT_SESSION_NOT_FOUND = "CHAT_SESSION_NOT_FOUND"
    
    # Business Logic Errors (400-422)
    TEST_ALREADY_COMPLETED = "TEST_ALREADY_COMPLETED"
    TEST_TIME_EXPIRED = "TEST_TIME_EXPIRED"
    INSUFFICIENT_QUESTIONS = "INSUFFICIENT_QUESTIONS"
    INVALID_TEST_CONFIGURATION = "INVALID_TEST_CONFIGURATION"
    DUPLICATE_ANSWER_SUBMISSION = "DUPLICATE_ANSWER_SUBMISSION"
    
    # File/Media Errors (400)
    MISSING_IMAGE = "MISSING_IMAGE"
    INVALID_IMAGE_TYPE = "INVALID_IMAGE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    
    # External Service Errors (502-504)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    EMAIL_SERVICE_ERROR = "EMAIL_SERVICE_ERROR"
    
    # OTP & Mobile Verification Errors
    OTP_INVALID = "OTP_INVALID"
    OTP_EXPIRED = "OTP_EXPIRED"
    OTP_RATE_LIMIT_EXCEEDED = "OTP_RATE_LIMIT_EXCEEDED"
    OTP_INVALID_MOBILE = "OTP_INVALID_MOBILE"
    OTP_INVALID_FORMAT = "OTP_INVALID_FORMAT"
    OTP_INVALID_REQUEST = "OTP_INVALID_REQUEST"
    INVALID_MOBILE_NUMBER = "INVALID_MOBILE_NUMBER"
    SMS_SERVICE_ERROR = "SMS_SERVICE_ERROR"
    
    # Rate Limiting (429)
    RATE_LIMITED = "RATE_LIMITED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Server Errors (500)
    SERVER_ERROR = "SERVER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


# Error code to HTTP status mapping
ERROR_CODE_STATUS_MAP = {
    # Authentication & Authorization
    ErrorCodes.AUTH_REQUIRED: 401,
    ErrorCodes.AUTH_INVALID_CREDENTIALS: 401,
    ErrorCodes.AUTH_TOKEN_EXPIRED: 401,
    ErrorCodes.AUTH_TOKEN_INVALID: 401,
    ErrorCodes.AUTH_FORBIDDEN: 403,
    ErrorCodes.AUTH_GOOGLE_TOKEN_INVALID: 401,
    
    # Input Validation
    ErrorCodes.INVALID_INPUT: 400,
    ErrorCodes.MISSING_REQUIRED_FIELD: 400,
    ErrorCodes.INVALID_EMAIL_FORMAT: 400,
    ErrorCodes.INVALID_PASSWORD: 400,
    ErrorCodes.INVALID_STUDENT_ID: 400,
    
    # Resource Errors
    ErrorCodes.NOT_FOUND: 404,
    ErrorCodes.STUDENT_NOT_FOUND: 404,
    ErrorCodes.TEST_SESSION_NOT_FOUND: 404,
    ErrorCodes.QUESTION_NOT_FOUND: 404,
    ErrorCodes.TOPIC_NOT_FOUND: 404,
    ErrorCodes.CHAT_SESSION_NOT_FOUND: 404,
    
    # Business Logic
    ErrorCodes.TEST_ALREADY_COMPLETED: 422,
    ErrorCodes.TEST_TIME_EXPIRED: 422,
    ErrorCodes.INSUFFICIENT_QUESTIONS: 422,
    ErrorCodes.INVALID_TEST_CONFIGURATION: 400,
    ErrorCodes.DUPLICATE_ANSWER_SUBMISSION: 422,
    
    # File/Media
    ErrorCodes.MISSING_IMAGE: 400,
    ErrorCodes.INVALID_IMAGE_TYPE: 400,
    ErrorCodes.FILE_TOO_LARGE: 413,
    
    # External Services
    ErrorCodes.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCodes.AI_SERVICE_UNAVAILABLE: 503,
    ErrorCodes.DATABASE_CONNECTION_ERROR: 503,
    ErrorCodes.EMAIL_SERVICE_ERROR: 502,
    
    # OTP & Mobile Verification
    ErrorCodes.OTP_INVALID: 400,
    ErrorCodes.OTP_EXPIRED: 400,
    ErrorCodes.OTP_RATE_LIMIT_EXCEEDED: 429,
    ErrorCodes.OTP_INVALID_MOBILE: 400,
    ErrorCodes.OTP_INVALID_FORMAT: 400,
    ErrorCodes.OTP_INVALID_REQUEST: 400,
    ErrorCodes.INVALID_MOBILE_NUMBER: 400,
    ErrorCodes.SMS_SERVICE_ERROR: 502,
    
    # Rate Limiting
    ErrorCodes.RATE_LIMITED: 429,
    ErrorCodes.TOO_MANY_REQUESTS: 429,
    ErrorCodes.RATE_LIMIT_EXCEEDED: 429,
    
    # Validation
    ErrorCodes.VALIDATION_ERROR: 400,
    
    # Server Errors
    ErrorCodes.SERVER_ERROR: 500,
    ErrorCodes.INTERNAL_ERROR: 500,
    ErrorCodes.CONFIGURATION_ERROR: 500,
}


def get_status_code(error_code: str) -> int:
    """
    Get HTTP status code for a given error code.
    
    Args:
        error_code: The error code string
        
    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    return ERROR_CODE_STATUS_MAP.get(error_code, 500)

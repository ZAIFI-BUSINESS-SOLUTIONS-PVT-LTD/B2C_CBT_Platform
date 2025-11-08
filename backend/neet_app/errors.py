"""
Custom error classes and exception handling for the NEET Practice Platform.

This module provides a standardized way to handle errors throughout the application.
All errors should use the AppError class to ensure consistent error responses.
"""

import logging
from typing import Any, Dict, Optional
from django.utils import timezone

from .error_codes import ErrorCodes, get_status_code

logger = logging.getLogger(__name__)


class AppError(Exception):
    """
    Custom application error class for standardized error handling.
    
    This class ensures all errors follow a consistent format:
    - code: Standardized error code from ErrorCodes
    - message: User-friendly error message
    - status_code: HTTP status code
    - details: Optional additional error details for debugging
    
    Usage:
        raise AppError(
            code=ErrorCodes.INVALID_INPUT,
            message="Email address is required",
            details={"field": "email"}
        )
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize AppError.
        
        Args:
            code: Error code from ErrorCodes class
            message: User-friendly error message
            status_code: HTTP status code (auto-determined if not provided)
            details: Optional additional error details
        """
        self.code = code
        self.message = message
        self.status_code = status_code or get_status_code(code)
        self.details = details or {}
        self.timestamp = timezone.now().isoformat()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary format for JSON serialization.
        
        Returns:
            Dictionary containing error information
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "timestamp": self.timestamp,
                "details": self.details if self.details else None
            }
        }
    
    def __str__(self) -> str:
        return f"AppError({self.code}): {self.message}"
    
    def __repr__(self) -> str:
        return f"AppError(code='{self.code}', message='{self.message}', status_code={self.status_code})"


class ValidationError(AppError):
    """Specific error for input validation failures.

    This class is a thin wrapper over AppError that defaults to
    ErrorCodes.INVALID_INPUT but also allows callers to override
    the `code` and `status_code` when needed (some callsites pass
    a different code).
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field

        final_code = code or ErrorCodes.INVALID_INPUT

        super().__init__(
            code=final_code,
            message=message,
            status_code=status_code,
            details=error_details,
        )


class AuthenticationError(AppError):
    """Specific error for authentication failures."""
    
    def __init__(self, message: str = "Authentication required", code: str = ErrorCodes.AUTH_REQUIRED):
        super().__init__(
            code=code,
            message=message
        )


class AuthorizationError(AppError):
    """Specific error for authorization failures."""
    
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            code=ErrorCodes.AUTH_FORBIDDEN,
            message=message
        )


class NotFoundError(AppError):
    """Specific error for resource not found."""
    
    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None):
        code = ErrorCodes.NOT_FOUND
        if resource_type:
            # Map specific resource types to specific error codes
            resource_code_map = {
                "student": ErrorCodes.STUDENT_NOT_FOUND,
                "test_session": ErrorCodes.TEST_SESSION_NOT_FOUND,
                "question": ErrorCodes.QUESTION_NOT_FOUND,
                "topic": ErrorCodes.TOPIC_NOT_FOUND,
                "chat_session": ErrorCodes.CHAT_SESSION_NOT_FOUND,
            }
            code = resource_code_map.get(resource_type, ErrorCodes.NOT_FOUND)
        
        super().__init__(
            code=code,
            message=message
        )


class ExternalServiceError(AppError):
    """Specific error for external service failures."""
    
    def __init__(self, message: str = "External service unavailable", service_name: Optional[str] = None):
        details = {}
        if service_name:
            details["service"] = service_name
            
        super().__init__(
            code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
            message=message,
            details=details
        )


class BusinessLogicError(AppError):
    """Specific error for business rule violations."""
    
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            message=message,
            details=details
        )

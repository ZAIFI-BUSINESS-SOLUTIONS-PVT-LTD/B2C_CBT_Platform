"""
Global exception handler and middleware for standardized error responses.

This module provides centralized error handling that ensures all API responses
follow a consistent JSON format regardless of where the error originates.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    ParseError,
    UnsupportedMediaType,
    Throttled
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .errors import AppError
from .error_codes import ErrorCodes

logger = logging.getLogger(__name__)


def standard_exception_handler(exc, context):
    """
    Custom DRF exception handler that standardizes all error responses.
    
    This handler ensures all API errors return a consistent JSON format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "User-friendly message",
            "timestamp": "2025-09-09T12:00:00Z",
            "details": {...}  // Optional, only for development
        }
    }
    
    Args:
        exc: The exception that was raised
        context: Context information about the request
        
    Returns:
        Response object with standardized error format
    """
    timestamp = timezone.now().isoformat()
    request = context.get('request')
    
    # Log the error with context
    _log_error(exc, request, context)
    
    # Handle our custom AppError first
    if isinstance(exc, AppError):
        return Response(
            exc.to_dict(),
            status=exc.status_code
        )
    
    # Handle DRF built-in exceptions
    drf_response = exception_handler(exc, context)
    
    if drf_response is not None:
        error_data = _handle_drf_exception(exc, drf_response, timestamp)
        return Response(error_data, status=drf_response.status_code)
    
    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        error_data = _create_error_response(
            code=ErrorCodes.INVALID_INPUT,
            message="Validation failed",
            timestamp=timestamp,
            details={"validation_errors": exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}
        )
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle any other unhandled exceptions
    error_data = _create_error_response(
        code=ErrorCodes.SERVER_ERROR,
        message="An unexpected error occurred" if not settings.DEBUG else str(exc),
        timestamp=timestamp,
        details={"traceback": traceback.format_exc()} if settings.DEBUG else None
    )
    
    return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _handle_drf_exception(exc, drf_response, timestamp: str) -> Dict[str, Any]:
    """Handle DRF built-in exceptions and map to our error format."""
    
    # Map DRF exceptions to our error codes
    if isinstance(exc, NotAuthenticated):
        code = ErrorCodes.AUTH_REQUIRED
        message = "Authentication credentials were not provided"
    elif isinstance(exc, (AuthenticationFailed, InvalidToken, TokenError)):
        code = ErrorCodes.AUTH_TOKEN_INVALID
        message = "Authentication failed"
    elif isinstance(exc, PermissionDenied):
        code = ErrorCodes.AUTH_FORBIDDEN
        message = "Access forbidden"
    elif isinstance(exc, NotFound):
        code = ErrorCodes.NOT_FOUND
        message = "Resource not found"
    elif isinstance(exc, DRFValidationError):
        code = ErrorCodes.INVALID_INPUT
        message = "Validation failed"
        # Include validation details for client debugging
        details = {"validation_errors": exc.detail}
    elif isinstance(exc, ParseError):
        code = ErrorCodes.INVALID_INPUT
        message = "Invalid request format"
    elif isinstance(exc, UnsupportedMediaType):
        code = ErrorCodes.INVALID_INPUT
        message = "Unsupported media type"
    elif isinstance(exc, MethodNotAllowed):
        code = ErrorCodes.INVALID_INPUT
        message = "Method not allowed"
    elif isinstance(exc, Throttled):
        code = ErrorCodes.RATE_LIMITED
        message = "Rate limit exceeded"
    else:
        code = ErrorCodes.SERVER_ERROR
        message = "An error occurred"
    
    # Extract details from DRF response
    details = None
    if isinstance(drf_response.data, dict):
        details = drf_response.data
    elif isinstance(drf_response.data, list):
        details = {"errors": drf_response.data}
    
    return _create_error_response(code, message, timestamp, details)


def _create_error_response(
    code: str, 
    message: str, 
    timestamp: str, 
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create standardized error response format."""
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "timestamp": timestamp
        }
    }
    
    # Only include details if they exist and we're in debug mode or it's useful info
    if details and (settings.DEBUG or any(key in details for key in ['field', 'validation_errors'])):
        error_response["error"]["details"] = details
    
    return error_response


def _log_error(exc, request, context):
    """Log error with context information."""
    
    # Extract useful request information
    request_info = {}
    if request:
        request_info = {
            "method": request.method,
            "path": request.path,
            "user": getattr(request.user, 'id', 'anonymous') if hasattr(request, 'user') else 'unknown',
            "ip": _get_client_ip(request)
        }
    
    # Log based on exception type
    if isinstance(exc, AppError):
        logger.error(
            f"AppError: {exc.code} - {exc.message}",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "request_info": request_info,
                "details": exc.details
            }
        )
    else:
        logger.exception(
            f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "request_info": request_info
            }
        )


def _get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class ErrorHandlingMiddleware:
    """
    Django middleware for handling errors that occur outside of DRF views.
    
    This middleware catches any exceptions that aren't handled by the DRF
    exception handler and formats them according to our standard error format.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Process exceptions that occur outside of DRF views."""
        
        # Only handle exceptions for API endpoints
        if not request.path.startswith('/api/'):
            return None
        
        timestamp = timezone.now().isoformat()
        
        # Log the error
        logger.exception(
            f"Middleware caught exception: {type(exception).__name__} - {str(exception)}",
            extra={
                "exception_type": type(exception).__name__,
                "request_path": request.path,
                "request_method": request.method
            }
        )
        
        # Handle AppError
        if isinstance(exception, AppError):
            return JsonResponse(
                exception.to_dict(),
                status=exception.status_code
            )
        
        # Handle other exceptions
        error_data = _create_error_response(
            code=ErrorCodes.SERVER_ERROR,
            message="An unexpected error occurred",
            timestamp=timestamp
        )
        
        return JsonResponse(error_data, status=500)

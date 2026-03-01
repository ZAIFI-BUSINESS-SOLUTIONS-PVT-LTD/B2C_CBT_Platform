"""
Question Feedback Views
Handles student feedback on questions during tests
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import IntegrityError

from ..models import QuestionFeedback
from ..serializers import QuestionFeedbackCreateSerializer, QuestionFeedbackSerializer
from ..errors import AppError, ValidationError as AppValidationError
from ..error_codes import ErrorCodes


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_question_feedback(request):
    """
    Submit feedback for a question during a test
    
    POST /api/question-feedback/
    
    Request Body:
    {
        "testId": number,
        "questionId": number,
        "feedbackType": string,
        "remarks": string (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Feedback submitted successfully",
        "data": {...}
    }
    """
    # Get student_id from authenticated user
    if not hasattr(request.user, 'student_id'):
        raise AppError(
            message="User is not a student",
            error_code=ErrorCodes.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Use authenticated user's student_id instead of request body
    authenticated_student_id = request.user.student_id
    
    # Create serializer with request data (camelCase from frontend)
    serializer_data = {
        'student_id': authenticated_student_id,  # Use authenticated user's ID
        'test_id': request.data.get('testId') or request.data.get('test_id'),
        'question_id': request.data.get('questionId') or request.data.get('question_id'),
        'feedback_type': request.data.get('feedbackType') or request.data.get('feedback_type'),
        'remarks': request.data.get('remarks', ''),
    }
    
    serializer = QuestionFeedbackCreateSerializer(data=serializer_data)
    
    try:
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()
        
        # Return success response
        response_serializer = QuestionFeedbackSerializer(feedback)
        return Response({
            'success': True,
            'message': 'Feedback submitted successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError:
        # Duplicate feedback for same question in same test
        raise AppError(
            message="You have already submitted feedback for this question in this test",
            error_code=ErrorCodes.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        if isinstance(e, AppError):
            raise
        raise AppError(
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_question_feedback(request):
    """
    Get all feedback submitted by the authenticated student
    
    GET /api/question-feedback/
    
    Query Parameters:
    - test_id: Filter by test session ID (optional)
    - question_id: Filter by question ID (optional)
    
    Response:
    {
        "success": true,
        "data": [...]
    }
    """
    if not hasattr(request.user, 'student_id'):
        raise AppError(
            message="User is not a student",
            error_code=ErrorCodes.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get feedback for authenticated student
    queryset = QuestionFeedback.objects.filter(
        student__student_id=request.user.student_id
    ).select_related('student', 'test_session', 'question')
    
    # Optional filters
    test_id = request.query_params.get('test_id')
    if test_id:
        queryset = queryset.filter(test_session_id=test_id)
    
    question_id = request.query_params.get('question_id')
    if question_id:
        queryset = queryset.filter(question_id=question_id)
    
    # Order by most recent first
    queryset = queryset.order_by('-created_at')
    
    serializer = QuestionFeedbackSerializer(queryset, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

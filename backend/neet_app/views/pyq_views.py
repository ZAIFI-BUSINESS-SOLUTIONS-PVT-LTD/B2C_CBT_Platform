"""
Previous Year Question Paper (PYQ) views.
Handles PYQ upload, listing for both institutions and students, and test initiation.
"""

import logging
import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from neet_app.models import (
    PreviousYearQuestionPaper, 
    Question, 
    TestSession, 
    TestAnswer,
    InstitutionAdmin,
    StudentProfile
)
from neet_app.serializers import QuestionForTestSerializer, TestSessionSerializer
from neet_app.errors import AppError, ValidationError as AppValidationError
from neet_app.error_codes import ErrorCodes
from neet_app.services.pyq_import import process_pyq_upload, UploadValidationError
from neet_app.institution_auth import institution_admin_required

logger = logging.getLogger(__name__)


@csrf_exempt
@institution_admin_required
@require_http_methods(["POST"])
def upload_pyq(request):
    """
    Upload a Previous Year Question Paper (institution admin only).
    
    Expected form-data:
    - name: PYQ name (required)
    - file: Excel file (.xlsx) (required)
    - exam_type: Exam type, e.g., 'neet', 'jee' (optional)
    - notes: Optional description/notes (optional)
    
    Returns:
        JSON with pyq_id, questions_created, topics_used
    """
    # Get admin from request (added by decorator)
    admin = request.institution_admin
    
    # Extract form data
    pyq_name = request.POST.get('name', '').strip()
    exam_type = request.POST.get('exam_type', 'neet').strip().lower()
    notes = request.POST.get('notes', '').strip() or None
    
    # Validate inputs
    if not pyq_name:
        return JsonResponse(
            {'error': 'PYQ name is required'},
            status=400
        )
    
    # Get uploaded file
    if 'file' not in request.FILES:
        return JsonResponse(
            {'error': 'No file uploaded'},
            status=400
        )
    
    file_obj = request.FILES['file']
    
    # Validate file extension
    if not file_obj.name.endswith(('.xlsx', '.xls')):
        return JsonResponse(
            {'error': 'Only Excel files (.xlsx, .xls) are supported'},
            status=400
        )
    
    # Check for duplicate name within institution
    if PreviousYearQuestionPaper.objects.filter(
        institution=admin.institution,
        name=pyq_name
    ).exists():
        return JsonResponse(
            {'error': f'A PYQ with name "{pyq_name}" already exists for your institution'},
            status=400
        )
    
    # Process upload
    try:
        result = process_pyq_upload(
            file_obj=file_obj,
            institution=admin.institution,
            pyq_name=pyq_name,
            exam_type=exam_type,
            uploaded_by=admin,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f'PYQ "{pyq_name}" uploaded successfully',
            'pyq_id': result['pyq_id'],
            'pyq_name': result['pyq_name'],
            'questions_created': result['questions_created'],
            'topics_used': result['topics_used'],
            'exam_type': result['exam_type']
        }, status=201)
        
    except UploadValidationError as e:
        logger.warning(f"PYQ upload validation error: {str(e)}")
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except Exception as e:
        logger.exception(f"Unexpected error during PYQ upload: {str(e)}")
        return JsonResponse(
            {'error': 'Failed to process upload. Please check file format and try again.'},
            status=500
        )


@institution_admin_required
@require_http_methods(["GET"])
def list_institution_pyqs(request):
    """
    List all PYQs uploaded by the institution (institution admin only).
    
    Returns:
        JSON with list of PYQs and their metadata
    """
    # Get admin from request (added by decorator)
    admin = request.institution_admin
    
    # Get all PYQs for this institution
    pyqs = PreviousYearQuestionPaper.objects.filter(
        institution=admin.institution
    ).order_by('-uploaded_at')
    
    pyqs_data = []
    for pyq in pyqs:
        pyqs_data.append({
            'id': pyq.id,
            'name': pyq.name,
            'question_count': pyq.question_count,
            'exam_type': pyq.exam_type,
            'is_active': pyq.is_active,
            'uploaded_at': pyq.uploaded_at.isoformat(),
            'uploaded_by': pyq.uploaded_by.name if pyq.uploaded_by else 'Unknown',
            'source_filename': pyq.source_filename,
            'notes': pyq.notes
        })
    
    return JsonResponse({
        'pyqs': pyqs_data,
        'total_count': len(pyqs_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_student_pyqs(request):
    """
    List all active PYQs available to students.
    PYQs are globally accessible to all users regardless of institution membership.
    
    Returns:
        JSON with list of available PYQs
    """
    # Show all active PYQs to all students (global access like institution tests)
    # PYQs created by any institution should be visible to all users
    pyqs = PreviousYearQuestionPaper.objects.filter(
        is_active=True
    ).order_by('-uploaded_at')
    
    pyqs_data = []
    for pyq in pyqs:
        # Count how many times this student has attempted this PYQ
        attempt_count = 0
        if hasattr(request.user, 'student_id'):
            attempt_count = TestSession.objects.filter(
                student_id=request.user.student_id,
                test_type='pyq',
                selected_topics__contains=[pyq.id]  # Store pyq_id in selected_topics for tracking
            ).count()
        
        pyqs_data.append({
            'id': pyq.id,
            'name': pyq.name,
            'question_count': pyq.question_count,
            'exam_type': pyq.exam_type,
            'uploaded_at': pyq.uploaded_at.isoformat(),
            'notes': pyq.notes,
            'attempt_count': attempt_count,
        })
    
    return Response({
        'pyqs': pyqs_data,
        'total_count': len(pyqs_data)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_pyq_test(request, pyq_id):
    """
    Start a PYQ test session.
    Creates a new TestSession and assigns questions.
    
    Unlike platform tests, PYQs:
    - Allow unlimited retakes (no "already completed" check)
    - Have no expiry date
    - Use preserved upload order for questions
    
    Returns:
        JSON with session details and questions
    """
    # Get PYQ
    try:
        pyq = PreviousYearQuestionPaper.objects.select_related('institution').get(
            id=pyq_id,
            is_active=True
        )
    except PreviousYearQuestionPaper.DoesNotExist:
        raise AppError(
            code=ErrorCodes.NOT_FOUND,
            message='PYQ not found or inactive'
        )
    
    # Get student ID from authenticated user
    if not hasattr(request.user, 'student_id'):
        raise AppError(
            code=ErrorCodes.AUTH_REQUIRED,
            message='User not properly authenticated'
        )
    
    student_id = request.user.student_id
    
    # Check if student already has an ACTIVE session for this PYQ (prevent simultaneous attempts)
    existing_active_session = TestSession.objects.filter(
        student_id=student_id,
        test_type='pyq',
        selected_topics__contains=[pyq.id],
        is_completed=False
    ).first()
    
    if existing_active_session:
        raise AppError(
            code=ErrorCodes.INVALID_INPUT,
            message='You already have an active session for this PYQ. Please complete or exit it first.',
            details={'session_id': existing_active_session.id}
        )
    
    # NOTE: We do NOT check for completed sessions - unlimited retakes allowed for PYQs
    
    # Get questions for this PYQ (preserve upload order by ordering by id)
    questions = pyq.get_questions()
    question_count = questions.count()
    
    if question_count == 0:
        raise AppValidationError(
            code=ErrorCodes.INSUFFICIENT_QUESTIONS,
            message='No questions available for this PYQ'
        )
    
    # Create test session
    # Store the pyq_id in selected_topics for tracking (even though it's not a topic ID)
    # This is a lightweight hack to avoid adding a new FK field
    test_session = TestSession.objects.create(
        student_id=student_id,
        test_type='pyq',
        selected_topics=[pyq.id],  # Store PYQ ID for tracking
        time_limit=question_count * 2,  # Default: 2 minutes per question
        question_count=question_count,
        start_time=timezone.now(),
        total_questions=question_count
    )
    
    # Create TestAnswer records for all questions (preserve order)
    test_answer_objs = []
    for question in questions:
        test_answer_objs.append(TestAnswer(
            session=test_session,
            question=question,
            selected_answer=None,
            is_correct=False,
            marked_for_review=False,
            time_taken=0
        ))
    TestAnswer.objects.bulk_create(test_answer_objs)
    
    # Serialize session and questions
    session_serialized = TestSessionSerializer(test_session).data
    questions_serialized = QuestionForTestSerializer(questions, many=True).data
    
    return Response({
        'message': 'PYQ test session started successfully',
        'session_id': test_session.id,
        'session': session_serialized,
        'questions': questions_serialized,
        'pyq_info': {
            'pyq_id': pyq.id,
            'pyq_name': pyq.name,
            'question_count': question_count,
            'exam_type': pyq.exam_type,
            'notes': pyq.notes
        }
    }, status=status.HTTP_201_CREATED)


@csrf_exempt
@institution_admin_required
@require_http_methods(["DELETE"])
def delete_pyq(request, pyq_id):
    """
    Soft-delete a PYQ (institution admin only).
    Sets is_active=False instead of actually deleting.
    """
    # Get admin from request (added by decorator)
    admin = request.institution_admin
    
    # Get PYQ and verify ownership
    try:
        pyq = PreviousYearQuestionPaper.objects.get(
            id=pyq_id,
            institution=admin.institution
        )
    except PreviousYearQuestionPaper.DoesNotExist:
        return JsonResponse(
            {'error': 'PYQ not found or does not belong to your institution'},
            status=404
        )
    
    # Soft delete
    pyq.is_active = False
    pyq.save(update_fields=['is_active'])
    
    return JsonResponse({
        'success': True,
        'message': f'PYQ "{pyq.name}" has been deactivated'
    })

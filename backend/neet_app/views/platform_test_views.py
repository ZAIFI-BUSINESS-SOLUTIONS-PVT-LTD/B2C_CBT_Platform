from django.utils import timezone
import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..errors import AppError, ValidationError as AppValidationError
from ..error_codes import ErrorCodes

from ..models import PlatformTest, TestSession, TestAnswer
from ..serializers import TestSessionSerializer, QuestionForTestSerializer

# local imports for question generation utilities will be performed inline to avoid circular imports


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_available_platform_tests(request):
    """
    List all platform tests available to students.
    Shows both scheduled and open tests with their availability status.
    """
    # Get all active platform tests
    platform_tests = PlatformTest.objects.filter(is_active=True).order_by('scheduled_date_time', 'test_name')
    
    tests_data = []
    # Determine authenticated student's id if available
    student_id = getattr(request.user, 'student_id', None)

    for test in platform_tests:
        # Per-student flags
        has_completed = False
        has_active_session = False
        if student_id:
            has_completed = TestSession.objects.filter(
                student_id=student_id,
                platform_test=test,
                is_completed=True
            ).exists()
            has_active_session = TestSession.objects.filter(
                student_id=student_id,
                platform_test=test,
                is_completed=False
            ).exists()

        test_data = {
            'id': test.id,
            'test_name': test.test_name,
            'test_code': test.test_code,
            'description': test.description,
            'instructions': test.instructions,
            'duration': test.time_limit,  # Duration in minutes
            'total_questions': test.total_questions,
            'test_year': test.test_year,
            'test_type': test.test_type,
            'scheduled_date_time': test.scheduled_date_time.isoformat() if test.scheduled_date_time else None,
            'is_scheduled': test.is_scheduled_test(),
            'is_open': test.is_open_test(),
            'is_available_now': test.is_available_now(),
            'availability_status': test.get_availability_status(),
            'has_completed': has_completed,
            'has_active_session': has_active_session,
            'created_at': test.created_at.isoformat(),
        }
        tests_data.append(test_data)
    
    # Separate scheduled and open tests for better frontend organization
    scheduled_tests = [test for test in tests_data if test['is_scheduled']]
    open_tests = [test for test in tests_data if test['is_open']]
    
    return Response({
        'scheduled_tests': scheduled_tests,
        'open_tests': open_tests,
        'total_tests': len(tests_data),
        'current_time': timezone.now().isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_platform_test(request, test_id):
    """
    Start a platform test attempt.
    Creates a new TestSession linked to the PlatformTest.
    Includes institution membership checks for institution tests.
    """
    try:
        platform_test = PlatformTest.objects.select_related('institution').get(id=test_id, is_active=True)
    except PlatformTest.DoesNotExist:
        raise AppError(code=ErrorCodes.NOT_FOUND, message='Platform test not found or inactive.')
    
    # Check if this is an institution test and verify student has access
    if platform_test.is_institution_test and platform_test.institution:
        # Get student profile to check institution membership
        from ..models import StudentProfile
        try:
            student_profile = StudentProfile.objects.get(student_id=request.user.student_id)
            
            # Check if student is linked to this institution
            if student_profile.institution != platform_test.institution:
                # Student is not linked to the institution - deny access
                # Use standardized auth error code from ErrorCodes
                raise AppError(
                    code=ErrorCodes.AUTH_FORBIDDEN,
                    message='You do not have access to this institution test. Please verify your institution code first.',
                    details={
                        'required_institution': platform_test.institution.name,
                        'institution_code_required': True
                    }
                )
        except StudentProfile.DoesNotExist:
            raise AppError(code=ErrorCodes.AUTH_REQUIRED, message='Student profile not found')
    
    # Check if test is available now
    if not platform_test.is_available_now():
        raise AppError(code=ErrorCodes.INVALID_TEST_CONFIGURATION, message='Test is not available at this time.', details={'availability_status': platform_test.get_availability_status(), 'scheduled_date_time': platform_test.scheduled_date_time.isoformat() if platform_test.scheduled_date_time else None})
    
    # Get student ID from authenticated user
    if not hasattr(request.user, 'student_id'):
        raise AppError(code=ErrorCodes.AUTH_REQUIRED, message='User not properly authenticated')
    
    student_id = request.user.student_id
    
    # Check if student already has an active session for this platform test
    existing_session = TestSession.objects.filter(
        student_id=student_id,
        platform_test=platform_test,
        is_completed=False
    ).first()
    
    if existing_session:
        raise AppError(code=ErrorCodes.TEST_ALREADY_COMPLETED if hasattr(ErrorCodes, 'TEST_ALREADY_COMPLETED') else ErrorCodes.INVALID_INPUT, message='You already have an active session for this test.', details={'session_id': existing_session.id, 'session': TestSessionSerializer(existing_session).data})

    # Check if the student has already completed this platform test; if so, disallow retake
    completed_session = TestSession.objects.filter(
        student_id=student_id,
        platform_test=platform_test,
        is_completed=True
    ).order_by('-end_time').first()

    if completed_session:
        # Student has already completed this platform test; do not allow another attempt
        raise AppError(code=ErrorCodes.TEST_ALREADY_COMPLETED, message='You have already completed this test and cannot retake it.', details={'completed_session_id': completed_session.id, 'completed_at': completed_session.end_time.isoformat() if completed_session.end_time else None})
    
    # Create new test session
    test_session = TestSession.objects.create(
        student_id=student_id,
        test_type='platform',
        platform_test=platform_test,
        selected_topics=platform_test.selected_topics,
        time_limit=platform_test.time_limit,
        question_count=platform_test.total_questions,
        start_time=timezone.now(),
        total_questions=platform_test.total_questions
    )
    
    # Update subject classification (this happens automatically via signals)
    test_session.update_subject_classification()
    test_session.save()
    
    # --- Ensure the session has actual assigned questions (same logic as TestSessionViewSet.create) ---
    try:
        # Import selection utilities here
        from .utils import generate_questions_for_topics
        from ..models import Question

        # For institution tests, filter questions by institution
        if platform_test.is_institution_test and platform_test.institution:
            # Get institution-specific questions for this test
            # Preserve upload/creation order for institution tests by ordering by primary key (id)
            # Questions are created in upload order, so ordering by 'id' will reflect that sequence.
            available_questions_qs = Question.objects.filter(
                institution=platform_test.institution,
                institution_test_name=platform_test.test_name,
                exam_type=platform_test.exam_type
            ).order_by('id')
            available_questions_list = list(available_questions_qs)
            available_count = len(available_questions_list)
        else:
            # For regular platform tests, use the existing selection logic
            # Determine available questions for the selected topics (do NOT exclude recent questions)
            # We convert to a list so we can randomly sample from it.
            available_questions_qs = generate_questions_for_topics(
                test_session.selected_topics,
                test_session.question_count,  # request per-difficulty selection for this many questions
                None,
                platform_test.difficulty_distribution
            )
            available_questions_list = list(available_questions_qs)
            available_count = len(available_questions_list)

        if available_count == 0:
            # No questions available for this platform test; mark session and return error
            test_session.delete()
            raise AppValidationError(code=ErrorCodes.INSUFFICIENT_QUESTIONS if hasattr(ErrorCodes, 'INSUFFICIENT_QUESTIONS') else ErrorCodes.INVALID_INPUT, message='No questions available for this platform test.', details={'available_questions': 0, 'requested_questions': platform_test.total_questions})

        # If fewer questions are available than configured, adjust counts to available
        if available_count < test_session.question_count:
            test_session.question_count = available_count
            test_session.total_questions = available_count
            test_session.save(update_fields=['question_count', 'total_questions'])

        # Select the final set of questions from the available pool.
        # For institution tests, preserve upload order (questions already ordered by 'id')
        if platform_test.is_institution_test and platform_test.institution:
            if available_count <= test_session.question_count:
                selected_questions = available_questions_list
            else:
                # Take the first N questions in the original upload order
                selected_questions = available_questions_list[:test_session.question_count]
        else:
            # For regular platform tests, keep existing behavior (random sampling for diversity)
            if available_count <= test_session.question_count:
                selected_questions = available_questions_list
            else:
                # random.sample returns a list of unique items of length question_count
                selected_questions = random.sample(available_questions_list, test_session.question_count)

        # Create TestAnswer records for the assigned questions (initially unanswered)
        test_answer_objs = []
        for q in selected_questions:
            test_answer_objs.append(TestAnswer(
                session=test_session,
                question=q,
                selected_answer=None,
                is_correct=False,
                marked_for_review=False,
                time_taken=0
            ))
        TestAnswer.objects.bulk_create(test_answer_objs)

    except Exception as e:
        # If any error occurs while assigning questions, delete the session to avoid orphan
        test_session.delete()
        raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to assign questions to session', details={'exception': str(e)})
    
    # Serialize session and the assigned questions for immediate consumption by the client
    session_serialized = TestSessionSerializer(test_session).data
    questions_serialized = QuestionForTestSerializer(selected_questions, many=True).data

    return Response(
        {
            'message': 'Platform test session started successfully.',
            'session_id': test_session.id,
            'session': session_serialized,
            'questions': questions_serialized,
            'test_info': {
                'test_name': platform_test.test_name,
                'duration': platform_test.time_limit,
                'total_questions': test_session.total_questions,
                'instructions': platform_test.instructions
            }
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_available_topics(request):
    """
    Return list of available topics (id and name) so admin can choose topics by name instead of IDs.
    """
    from ..models import Topic

    topics = Topic.objects.all().order_by('subject', 'name')
    topics_list = [{'id': t.id, 'name': t.name, 'subject': t.subject, 'chapter': t.chapter} for t in topics]
    return Response({'topics': topics_list})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_platform_test_details(request, test_id):
    """
    Get detailed information about a specific platform test.
    """
    try:
        platform_test = PlatformTest.objects.get(id=test_id, is_active=True)
    except PlatformTest.DoesNotExist:
        return Response(
            {'error': 'Platform test not found or inactive.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get student's attempt history for this test
    student_id = getattr(request.user, 'student_id', None)
    user_attempts = []
    
    if student_id:
        attempts = TestSession.objects.filter(
            student_id=student_id,
            platform_test=platform_test
        ).order_by('-start_time')
        
        for attempt in attempts:
            user_attempts.append({
                'session_id': attempt.id,
                'start_time': attempt.start_time.isoformat(),
                'end_time': attempt.end_time.isoformat() if attempt.end_time else None,
                'is_completed': attempt.is_completed,
                'score_percentage': attempt.calculate_score_percentage(),
                'correct_answers': attempt.correct_answers,
                'total_questions': attempt.total_questions
            })
    
    test_data = {
        'id': platform_test.id,
        'test_name': platform_test.test_name,
        'test_code': platform_test.test_code,
        'description': platform_test.description,
        'instructions': platform_test.instructions,
        'duration': platform_test.time_limit,
        'total_questions': platform_test.total_questions,
        'test_year': platform_test.test_year,
        'test_type': platform_test.test_type,
        'scheduled_date_time': platform_test.scheduled_date_time.isoformat() if platform_test.scheduled_date_time else None,
        'is_scheduled': platform_test.is_scheduled_test(),
        'is_open': platform_test.is_open_test(),
        'is_available_now': platform_test.is_available_now(),
        'availability_status': platform_test.get_availability_status(),
        'selected_topics': platform_test.selected_topics,
        'question_distribution': platform_test.question_distribution,
        'user_attempts': user_attempts,
        'total_user_attempts': len(user_attempts),
        'created_at': platform_test.created_at.isoformat(),
    }
    
    return Response(test_data)

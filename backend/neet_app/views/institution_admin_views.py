"""
Institution admin API views.
Handles login, test upload, and test management for institution administrators.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from neet_app.models import InstitutionAdmin, Institution, PlatformTest, Question
from neet_app.institution_auth import (
    generate_institution_admin_tokens,
    institution_admin_required
)
from neet_app.services.institution_upload import process_upload, UploadValidationError
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def institution_admin_login(request):
    """
    Institution admin login endpoint.
    
    POST /api/institution-admin/login
    Body: { "username": "admin_username", "password": "password" }
    
    Returns: { "access": "token", "refresh": "token", "admin": {...}, "institution": {...} }
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({
                'error': 'INVALID_INPUT',
                'message': 'Username and password are required'
            }, status=400)
        
        # Find institution admin
        try:
            admin = InstitutionAdmin.objects.select_related('institution').get(
                username=username
            )
        except InstitutionAdmin.DoesNotExist:
            return JsonResponse({
                'error': 'INVALID_CREDENTIALS',
                'message': 'Invalid username or password'
            }, status=401)
        
        # Check if active
        if not admin.is_active:
            return JsonResponse({
                'error': 'ACCOUNT_INACTIVE',
                'message': 'This account is inactive'
            }, status=403)
        
        # Verify password
        if not admin.check_password(password):
            return JsonResponse({
                'error': 'INVALID_CREDENTIALS',
                'message': 'Invalid username or password'
            }, status=401)
        
        # Generate tokens
        tokens = generate_institution_admin_tokens(admin)
        
        # Return success response
        return JsonResponse({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'admin': {
                'id': admin.id,
                'username': admin.username,
                'institution_id': admin.institution.id
            },
            'institution': {
                'id': admin.institution.id,
                'name': admin.institution.name,
                'code': admin.institution.code,
                'exam_types': admin.institution.exam_types
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception("Error in institution admin login")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)


@institution_admin_required
@require_http_methods(["GET"])
def get_exam_types(request):
    """
    Get available exam types for the institution.
    
    GET /api/institution-admin/exam-types
    
    Returns: { "exam_types": ["neet", "jee"] }
    """
    institution = request.institution
    
    # Return exam types from institution or default list
    exam_types = institution.exam_types or ['neet', 'jee']
    
    return JsonResponse({
        'exam_types': exam_types
    }, status=200)


@csrf_exempt
@institution_admin_required
@require_http_methods(["POST"])
def upload_test(request):
    """
    Upload Excel file with questions and create a test.
    
    POST /api/institution-admin/upload
    Content-Type: multipart/form-data
    Fields:
        - file: Excel file (.xlsx)
        - test_name: Name of the test
        - exam_type: Exam type (e.g., 'neet', 'jee')
        - time_limit: Time limit in minutes (optional, default 180)
        - instructions: Test instructions (optional)
    
    Returns: {
        "success": true,
        "test_id": 123,
        "test_code": "INST_1_NEET_...",
        "test_name": "...",
        "questions_created": 50,
        "topics_used": [...]
    }
    """
    try:
        institution = request.institution
        admin = request.institution_admin
        
        # Get form data
        test_name = request.POST.get('test_name', '').strip()
        exam_type = request.POST.get('exam_type', '').strip().lower()
        time_limit = int(request.POST.get('time_limit', 180))
        instructions = request.POST.get('instructions', '').strip()
        
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({
                'error': 'MISSING_FILE',
                'message': 'No file uploaded'
            }, status=400)
        
        file_obj = request.FILES['file']
        
        # Validate inputs
        if not test_name:
            return JsonResponse({
                'error': 'INVALID_INPUT',
                'message': 'Test name is required'
            }, status=400)
        
        if not exam_type:
            return JsonResponse({
                'error': 'INVALID_INPUT',
                'message': 'Exam type is required'
            }, status=400)
        
        # Validate exam type is supported by institution
        allowed_exam_types = institution.exam_types or ['neet', 'jee']
        if exam_type not in allowed_exam_types:
            return JsonResponse({
                'error': 'INVALID_EXAM_TYPE',
                'message': f'Exam type must be one of: {", ".join(allowed_exam_types)}'
            }, status=400)
        
        # Validate file extension
        if not file_obj.name.endswith('.xlsx'):
            return JsonResponse({
                'error': 'INVALID_FILE_TYPE',
                'message': 'Only .xlsx files are supported'
            }, status=400)
        
        # Process upload
        try:
            # Optional scheduled datetime (ISO string expected)
            from django.utils.dateparse import parse_datetime
            scheduled_dt_raw = request.POST.get('scheduled_date_time')
            scheduled_dt = None
            if scheduled_dt_raw:
                scheduled_dt = parse_datetime(scheduled_dt_raw)

            result = process_upload(
                file_obj=file_obj,
                institution=institution,
                test_name=test_name,
                exam_type=exam_type,
                time_limit=time_limit,
                instructions=instructions or None,
                scheduled_date_time=scheduled_dt
            )
            
            logger.info(f"Institution {institution.name} (admin: {admin.username}) uploaded test: {result['test_code']}")
            
            return JsonResponse(result, status=201)
            
        except UploadValidationError as e:
            return JsonResponse({
                'error': 'VALIDATION_ERROR',
                'message': str(e)
            }, status=400)
        
    except ValueError as e:
        return JsonResponse({
            'error': 'INVALID_INPUT',
            'message': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.exception("Error in upload_test")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred during upload'
        }, status=500)


@institution_admin_required
@require_http_methods(["GET"])
def list_institution_tests(request):
    """
    List all tests created by this institution.
    
    GET /api/institution-admin/tests?exam_type=neet
    
    Returns: {
        "tests": [
            {
                "id": 1,
                "test_name": "...",
                "test_code": "...",
                "exam_type": "neet",
                "total_questions": 50,
                "time_limit": 180,
                "is_active": true,
                "created_at": "...",
                "attempts_count": 10
            },
            ...
        ]
    }
    """
    try:
        institution = request.institution
        exam_type = request.GET.get('exam_type', '').strip().lower()
        
        # Build query
        query = PlatformTest.objects.filter(
            institution=institution,
            is_institution_test=True
        ).order_by('-created_at')
        
        # Filter by exam type if provided
        if exam_type:
            query = query.filter(exam_type=exam_type)
        
        # Get tests
        tests = []
        for test in query:
            # Count test attempts (sessions)
            from neet_app.models import TestSession
            attempts_count = TestSession.objects.filter(
                platform_test=test,
                test_type='platform'
            ).count()
            
            tests.append({
                'id': test.id,
                'test_name': test.test_name,
                'test_code': test.test_code,
                'exam_type': test.exam_type,
                'total_questions': test.total_questions,
                'time_limit': test.time_limit,
                'scheduled_date_time': test.scheduled_date_time.isoformat() if test.scheduled_date_time else None,
                'is_active': test.is_active,
                'created_at': test.created_at.isoformat(),
                'attempts_count': attempts_count
            })
        
        return JsonResponse({
            'tests': tests,
            'count': len(tests)
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in list_institution_tests")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)


@csrf_exempt
@institution_admin_required
@require_http_methods(["PATCH"])
def toggle_test_status(request, test_id):
    """
    Toggle test active/inactive status.
    
    PATCH /api/institution-admin/tests/<test_id>/toggle
    
    Returns: { "success": true, "is_active": true/false }
    """
    try:
        institution = request.institution
        
        # Get test
        try:
            test = PlatformTest.objects.get(
                id=test_id,
                institution=institution,
                is_institution_test=True
            )
        except PlatformTest.DoesNotExist:
            return JsonResponse({
                'error': 'NOT_FOUND',
                'message': 'Test not found'
            }, status=404)
        
        # Toggle status
        test.is_active = not test.is_active
        test.save(update_fields=['is_active', 'updated_at'])
        
        logger.info(f"Test {test.test_code} status toggled to {'active' if test.is_active else 'inactive'}")
        
        return JsonResponse({
            'success': True,
            'is_active': test.is_active
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in toggle_test_status")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)


@institution_admin_required
@require_http_methods(["GET"])
def get_test_details(request, test_id):
    """
    Get detailed information about a specific test.
    
    GET /api/institution-admin/tests/<test_id>
    
    Returns: {
        "test": { ... },
        "questions": [ ... ],
        "statistics": { ... }
    }
    """
    try:
        institution = request.institution
        
        # Get test
        try:
            test = PlatformTest.objects.get(
                id=test_id,
                institution=institution,
                is_institution_test=True
            )
        except PlatformTest.DoesNotExist:
            return JsonResponse({
                'error': 'NOT_FOUND',
                'message': 'Test not found'
            }, status=404)
        
        # Get questions for this test
        questions = Question.objects.filter(
            institution=institution,
            institution_test_name=test.test_name,
            exam_type=test.exam_type
        ).select_related('topic')
        
        questions_data = []
        for q in questions:
            questions_data.append({
                'id': q.id,
                'question': q.question[:100] + '...' if len(q.question) > 100 else q.question,
                'topic': q.topic.name,
                'difficulty': q.difficulty,
                'correct_answer': q.correct_answer
            })
        
        # Get statistics
        from neet_app.models import TestSession
        sessions = TestSession.objects.filter(
            platform_test=test,
            test_type='platform'
        )
        
        completed_sessions = sessions.filter(is_completed=True)
        
        statistics = {
            'total_attempts': sessions.count(),
            'completed_attempts': completed_sessions.count(),
            'in_progress': sessions.filter(is_completed=False).count()
        }
        
        if completed_sessions.exists():
            from django.db.models import Avg
            avg_score = completed_sessions.aggregate(
                avg_correct=Avg('correct_answers')
            )['avg_correct']
            
            statistics['average_score'] = round(avg_score, 2) if avg_score else 0
        
        return JsonResponse({
            'test': {
                'id': test.id,
                'test_name': test.test_name,
                'test_code': test.test_code,
                'exam_type': test.exam_type,
                'description': test.description,
                'instructions': test.instructions,
                'time_limit': test.time_limit,
                'scheduled_date_time': test.scheduled_date_time.isoformat() if test.scheduled_date_time else None,
                'total_questions': test.total_questions,
                'is_active': test.is_active,
                'created_at': test.created_at.isoformat()
            },
            'questions': questions_data,
            'statistics': statistics
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in get_test_details")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)

"""
Student institution API views.
Handles institution code verification and institution test listing for students.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from neet_app.models import Institution, PlatformTest, StudentProfile
from neet_app.student_auth import student_jwt_required
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@student_jwt_required
@require_http_methods(["POST"])
def verify_institution_code(request):
    """
    Verify an institution code, return institution details, and automatically link the student.
    
    POST /api/institutions/verify-code
    Headers: Authorization: Bearer <student_jwt>
    Body: { "code": "INST_CODE_123" }
    
    Returns: {
        "success": true,
        "institution": {
            "id": 1,
            "name": "...",
            "code": "...",
            "exam_types": ["neet", "jee"]
        },
        "linked": true
    }
    """
    try:
        student = request.student
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        
        if not code:
            return JsonResponse({
                'error': 'INVALID_INPUT',
                'message': 'Institution code is required'
            }, status=400)
        
        # Find institution by code (case-insensitive)
        try:
            institution = Institution.objects.get(code__iexact=code)
        except Institution.DoesNotExist:
            return JsonResponse({
                'error': 'INVALID_CODE',
                'message': 'Invalid institution code'
            }, status=404)
        
        # Automatically link student to institution
        try:
            # `request.student` is the StudentProfile instance set by student_jwt_required
            if isinstance(student, StudentProfile):
                student_profile = student
            else:
                student_profile = StudentProfile.objects.get(student_id=student)

            student_profile.institution = institution
            student_profile.save(update_fields=['institution', 'updated_at'])
            logger.info(f"Student {getattr(student_profile, 'student_id', student)} automatically linked to institution {institution.name} via code verification")
            linked = True
        except StudentProfile.DoesNotExist:
            logger.warning(f"Student profile not found for {student} during institution code verification")
            linked = False
        
        # Return institution details
        return JsonResponse({
            'success': True,
            'institution': {
                'id': institution.id,
                'name': institution.name,
                'code': institution.code,
                'exam_types': institution.exam_types or ['neet', 'jee']
            },
            'linked': linked
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception("Error in verify_institution_code")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)


@student_jwt_required
@require_http_methods(["GET"])
def list_institution_tests(request, institution_id):
    """
    List all active tests for a specific institution.
    
    GET /api/institutions/<institution_id>/tests?exam_type=neet
    
    Returns: {
        "tests": [
            {
                "id": 1,
                "test_name": "...",
                "test_code": "...",
                "exam_type": "neet",
                "total_questions": 50,
                "time_limit": 180,
                "instructions": "...",
                "created_at": "..."
            },
            ...
        ]
    }
    """
    try:
        student = request.student
        exam_type = request.GET.get('exam_type', '').strip().lower()
        
        # Verify institution exists
        try:
            institution = Institution.objects.get(id=institution_id)
        except Institution.DoesNotExist:
            return JsonResponse({
                'error': 'NOT_FOUND',
                'message': 'Institution not found'
            }, status=404)
        
        # Build query for active institution tests
        query = PlatformTest.objects.filter(
            institution=institution,
            is_institution_test=True,
            is_active=True
        ).order_by('-created_at')
        
        # Filter by exam type if provided
        if exam_type:
            query = query.filter(exam_type=exam_type)
        
        # Get tests
        tests = []
        for test in query:
            tests.append({
                'id': test.id,
                'test_name': test.test_name,
                'test_code': test.test_code,
                'exam_type': test.exam_type,
                'total_questions': test.total_questions,
                'time_limit': test.time_limit,
                'instructions': test.instructions,
                'description': test.description,
                'created_at': test.created_at.isoformat()
            })
        
        return JsonResponse({
            'tests': tests,
            'count': len(tests),
            'institution': {
                'id': institution.id,
                'name': institution.name
            }
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in list_institution_tests")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)


@csrf_exempt
@student_jwt_required
@require_http_methods(["PATCH"])
def link_student_to_institution(request):
    """
    Link a student profile to an institution (optional - for permanent binding).
    
    PATCH /api/student/link-institution
    Body: { "institution_id": 1 }
    
    Returns: { "success": true, "institution": { ... } }
    """
    try:
        student = request.student
        data = json.loads(request.body)
        institution_id = data.get('institution_id')
        
        if not institution_id:
            return JsonResponse({
                'error': 'INVALID_INPUT',
                'message': 'Institution ID is required'
            }, status=400)
        
        # Verify institution exists
        try:
            institution = Institution.objects.get(id=institution_id)
        except Institution.DoesNotExist:
            return JsonResponse({
                'error': 'NOT_FOUND',
                'message': 'Institution not found'
            }, status=404)
        
        # Link student to institution
        if isinstance(student, StudentProfile):
            student_profile = student
        else:
            student_profile = StudentProfile.objects.get(student_id=student)

        student_profile.institution = institution
        student_profile.save(update_fields=['institution', 'updated_at'])

        logger.info(f"Student {getattr(student_profile, 'student_id', student)} linked to institution {institution.name}")
        
        return JsonResponse({
            'success': True,
            'institution': {
                'id': institution.id,
                'name': institution.name,
                'code': institution.code
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except StudentProfile.DoesNotExist:
        return JsonResponse({
            'error': 'NOT_FOUND',
            'message': 'Student profile not found'
        }, status=404)
    except Exception as e:
        logger.exception("Error in link_student_to_institution")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred'
        }, status=500)

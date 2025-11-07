"""
Institution registration API endpoint.
Allows new institutions to register and create their admin account.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from neet_app.models import Institution, InstitutionAdmin
from neet_app.institution_auth import generate_institution_admin_tokens
import json
import logging
import re

logger = logging.getLogger(__name__)


def generate_institution_code(name):
    """Generate a unique institution code from the name."""
    # Take first 3-4 letters of name, uppercase
    code_base = re.sub(r'[^A-Za-z]', '', name)[:4].upper()
    
    # Add a random suffix to ensure uniqueness
    import random
    import string
    suffix = ''.join(random.choices(string.digits, k=4))
    
    code = f"{code_base}{suffix}"
    
    # Ensure uniqueness
    counter = 1
    original_code = code
    while Institution.objects.filter(code=code).exists():
        code = f"{original_code}{counter}"
        counter += 1
    
    return code


@csrf_exempt
@require_http_methods(["POST"])
def register_institution(request):
    """
    Register a new institution and create an admin account.
    
    POST /api/institution-admin/register/
    Body: {
        "institution_name": "Acme Coaching Center",
        "admin_username": "acme_admin",
        "admin_password": "SecurePass123!",
        "exam_types": ["neet", "jee"],  // optional, defaults to ["neet"]
        "institution_code": "ACME2024"  // optional, auto-generated if not provided
    }
    
    Returns: {
        "success": true,
        "institution": { "id": 1, "name": "...", "code": "..." },
        "admin": { "id": 1, "username": "..." },
        "access": "jwt_token",
        "refresh": "jwt_refresh_token"
    }
    """
    try:
        data = json.loads(request.body)
        
        # Extract and validate required fields
        institution_name = data.get('institution_name', '').strip()
        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')
        exam_types = data.get('exam_types', ['neet'])
        institution_code = data.get('institution_code', '').strip().upper()
        
        # Validation
        errors = {}
        
        if not institution_name:
            errors['institution_name'] = 'Institution name is required'
        elif len(institution_name) < 3:
            errors['institution_name'] = 'Institution name must be at least 3 characters'
        
        if not admin_username:
            errors['admin_username'] = 'Admin username is required'
        elif len(admin_username) < 3:
            errors['admin_username'] = 'Username must be at least 3 characters'
        elif InstitutionAdmin.objects.filter(username=admin_username).exists():
            errors['admin_username'] = 'This username is already taken'
        
        if not admin_password:
            errors['admin_password'] = 'Password is required'
        elif len(admin_password) < 6:
            errors['admin_password'] = 'Password must be at least 6 characters'
        
        if not isinstance(exam_types, list) or len(exam_types) == 0:
            errors['exam_types'] = 'At least one exam type is required'
        else:
            # Validate exam types
            valid_exam_types = ['neet', 'jee']
            invalid_types = [et for et in exam_types if et.lower() not in valid_exam_types]
            if invalid_types:
                errors['exam_types'] = f'Invalid exam types: {", ".join(invalid_types)}. Valid types are: neet, jee'
        
        # Generate or validate institution code
        if institution_code:
            if len(institution_code) < 4:
                errors['institution_code'] = 'Institution code must be at least 4 characters'
            elif Institution.objects.filter(code=institution_code).exists():
                errors['institution_code'] = 'This institution code is already taken'
        else:
            institution_code = generate_institution_code(institution_name)
        
        if errors:
            return JsonResponse({
                'error': 'VALIDATION_ERROR',
                'message': 'Please fix the errors in your form',
                'errors': errors
            }, status=400)
        
        # Create institution
        try:
            institution = Institution.objects.create(
                name=institution_name,
                code=institution_code,
                exam_types=[et.lower() for et in exam_types],
                is_active=True
            )
            
            logger.info(f"Created institution: {institution.name} ({institution.code})")
            
        except Exception as e:
            logger.exception("Error creating institution")
            return JsonResponse({
                'error': 'DATABASE_ERROR',
                'message': 'Failed to create institution'
            }, status=500)
        
        # Create institution admin
        try:
            admin = InstitutionAdmin.objects.create(
                username=admin_username,
                institution=institution,
                is_active=True
            )
            admin.set_password(admin_password)
            admin.save()
            
            logger.info(f"Created institution admin: {admin.username} for {institution.name}")
            
        except Exception as e:
            logger.exception("Error creating institution admin")
            # Rollback: delete the institution if admin creation fails
            institution.delete()
            return JsonResponse({
                'error': 'DATABASE_ERROR',
                'message': 'Failed to create admin account'
            }, status=500)
        
        # Generate JWT tokens for immediate login
        tokens = generate_institution_admin_tokens(admin)
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Institution registered successfully',
            'institution': {
                'id': institution.id,
                'name': institution.name,
                'code': institution.code,
                'exam_types': institution.exam_types
            },
            'admin': {
                'id': admin.id,
                'username': admin.username,
                'institution_id': institution.id
            },
            'access': tokens['access'],
            'refresh': tokens['refresh']
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception("Error in institution registration")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred during registration'
        }, status=500)

"""
Institution JSON question update views.
Handles JSON file upload for updating question fields (especially images).
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from neet_app.models import Question, Institution
from neet_app.institution_auth import institution_admin_required
import json
import logging
import base64
import binascii
from typing import Optional

logger = logging.getLogger(__name__)


class JSONUpdateValidationError(Exception):
    """Custom exception for JSON update validation errors"""
    pass


# Allowed image columns that we will normalize
IMAGE_COLUMNS = {
    'question_image',
    'option_a_image',
    'option_b_image',
    'option_c_image',
    'option_d_image',
    'explanation_image',
}

# Allowed text columns that can be updated
ALLOWED_COLUMNS = {
    'question', 'option_a', 'option_b', 'option_c', 'option_d',
    'correct_answer', 'explanation', 'difficulty', 'question_type',
    'institution_test_name'
} | IMAGE_COLUMNS


def normalize_base64_field(val: Optional[str], field_name: str = 'image') -> Optional[str]:
    """
    Normalize JSON/Excel value into a raw base64 payload or None.
    
    Mirrors the logic from import_questions_from_json.py:
    - Accepts full data URI or raw base64
    - Strips prefix, surrounding quotes, whitespace/newlines
    - Performs a quick validation using base64.b64decode(..., validate=True)
    
    Returns the cleaned base64 string (no data: prefix) or None if invalid/empty.
    """
    if val is None:
        return None
    try:
        s = str(val).strip()
        if not s:
            return None

        # If it's a data URI like data:image/png;base64,AAAA..., strip prefix
        if s.startswith('data:'):
            parts = s.split(',', 1)
            if len(parts) == 2:
                s = parts[1]
            else:
                logger.warning(f"{field_name}: Invalid data URI format (no comma found)")
                return None

        # Remove surrounding quotes
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1]

        # Remove internal whitespace/newlines
        s = ''.join(s.split())

        if not s:
            logger.warning(f"{field_name}: Empty after normalization")
            return None

        # Quick validation: decode small prefix/suffix to confirm it's valid base64
        try:
            # Validate first chunk
            base64.b64decode(s[:512], validate=True)
            # Validate last chunk if long
            if len(s) > 1024:
                base64.b64decode(s[-512:], validate=True)
        except (binascii.Error, ValueError) as e:
            logger.warning(f"{field_name}: Invalid base64 payload - {e}. Prefix: {s[:100]}")
            return None

        return s
    except Exception as e:
        logger.exception(f"Error normalizing base64 {field_name}: {e}")
        return None


def parse_json_updates(json_data):
    """
    Parse JSON array with update records.
    
    Expected format per record:
    {
        "question_id": 123,      // Question number (1-based index in test)
        "column_name": "question_image",
        "value": "data:image/png;base64,..."
    }
    
    Returns:
        list of dicts with validated records
    """
    if not isinstance(json_data, list):
        raise JSONUpdateValidationError("JSON must be an array of update records")
    
    if not json_data:
        raise JSONUpdateValidationError("JSON array is empty")
    
    parsed_records = []
    
    for idx, rec in enumerate(json_data, start=1):
        if not isinstance(rec, dict):
            raise JSONUpdateValidationError(f"Record {idx}: Must be a JSON object")
        
        question_id = rec.get('question_id')
        column_name = rec.get('column_name')
        value_raw = rec.get('value')
        
        # Validate question_id
        if question_id is None:
            raise JSONUpdateValidationError(f"Record {idx}: Missing 'question_id'")
        
        try:
            question_id = int(question_id)
            if question_id < 1:
                raise ValueError("Must be positive")
        except (ValueError, TypeError):
            raise JSONUpdateValidationError(
                f"Record {idx}: Invalid 'question_id' value '{question_id}'. Must be a positive integer."
            )
        
        # Validate column_name
        if not column_name:
            raise JSONUpdateValidationError(f"Record {idx}: Missing 'column_name'")
        
        if column_name not in ALLOWED_COLUMNS:
            raise JSONUpdateValidationError(
                f"Record {idx}: Invalid column '{column_name}'. Allowed columns: {', '.join(sorted(ALLOWED_COLUMNS))}"
            )
        
        parsed_records.append({
            'question_id': question_id,
            'column_name': column_name,
            'value_raw': value_raw,
            'record_index': idx
        })
    
    return parsed_records


def calculate_question_offset(institution, test_name):
    """
    Calculate the question ID offset for a given test.
    
    Logic:
    1. Filter questions by institution and test_name
    2. Order by ID ascending
    3. Get the first question's ID
    4. Offset = first_id - 1
    
    Returns:
        int: The offset value
    """
    questions = Question.objects.filter(
        institution=institution,
        institution_test_name=test_name
    ).order_by('id')
    
    if not questions.exists():
        raise JSONUpdateValidationError(
            f"No questions found for test '{test_name}' in institution '{institution.name}'"
        )
    
    first_question = questions.first()
    offset = first_question.id - 1
    
    logger.info(f"Calculated offset for test '{test_name}': {offset} (first question ID: {first_question.id})")
    
    return offset


def update_questions_from_json(institution, test_name, json_records):
    """
    Update Question records from parsed JSON data.
    
    Args:
        institution: Institution instance
        test_name: Test name string
        json_records: List of parsed update records
    
    Returns:
        dict with update statistics
    """
    # Calculate the offset dynamically
    offset = calculate_question_offset(institution, test_name)
    
    success_count = 0
    skipped_count = 0
    error_details = []
    
    for rec in json_records:
        question_id = rec['question_id']
        column_name = rec['column_name']
        value_raw = rec['value_raw']
        record_index = rec['record_index']
        
        # Calculate target DB primary key
        target_pk = offset + question_id
        
        logger.info(
            f"Processing record {record_index}: question_id={question_id}, "
            f"target_pk={target_pk}, column={column_name}"
        )
        
        # Find question
        try:
            question = Question.objects.get(
                pk=target_pk,
                institution=institution,
                institution_test_name=test_name
            )
        except Question.DoesNotExist:
            error_msg = (
                f"Record {record_index}: Question not found with "
                f"ID={target_pk} (question_id={question_id} + offset={offset})"
            )
            logger.warning(error_msg)
            error_details.append(error_msg)
            skipped_count += 1
            continue
        
        # Normalize value based on column type
        value_to_store = None
        if column_name in IMAGE_COLUMNS:
            value_to_store = normalize_base64_field(value_raw, field_name=column_name)
            if value_to_store is None:
                logger.warning(
                    f"Record {record_index}: Normalized value for {column_name} is invalid. "
                    "Will store NULL for this field."
                )
        else:
            # For non-image fields, store value as-is
            value_to_store = value_raw
        
        # Update the question
        try:
            with transaction.atomic():
                setattr(question, column_name, value_to_store)
                question.save(update_fields=[column_name])
            
            success_count += 1
            logger.info(f"✅ Updated question {question_id} (DB ID: {target_pk}): {column_name}")
            
        except Exception as e:
            error_msg = f"Record {record_index}: Failed to update question {question_id}: {str(e)}"
            logger.exception(error_msg)
            error_details.append(error_msg)
            skipped_count += 1
            continue
    
    return {
        'total_records': len(json_records),
        'success_count': success_count,
        'skipped_count': skipped_count,
        'offset_used': offset,
        'error_details': error_details
    }


@csrf_exempt
@institution_admin_required
@require_http_methods(["POST"])
def upload_json_updates(request):
    """
    Upload JSON file to update question fields.
    
    POST /api/institution-admin/upload-json-updates/
    Content-Type: multipart/form-data
    Fields:
        - file: JSON file with update records
        - test_name: Name of the test
    
    Returns: {
        "success": true,
        "test_name": "...",
        "total_records": 50,
        "success_count": 48,
        "skipped_count": 2,
        "offset_used": 908,
        "error_details": [...]
    }
    """
    try:
        institution = request.institution
        admin = request.institution_admin
        
        # Get form data
        test_name = request.POST.get('test_name', '').strip()
        
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
        
        # Validate file extension
        if not file_obj.name.endswith('.json'):
            return JsonResponse({
                'error': 'INVALID_FILE_TYPE',
                'message': 'Only .json files are supported'
            }, status=400)
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        
        if size > max_size:
            return JsonResponse({
                'error': 'FILE_TOO_LARGE',
                'message': 'File size must be less than 10MB'
            }, status=400)
        
        # Parse JSON file
        try:
            json_data = json.load(file_obj)
        except json.JSONDecodeError as e:
            return JsonResponse({
                'error': 'INVALID_JSON',
                'message': f'Failed to parse JSON file: {str(e)}'
            }, status=400)
        
        # Parse and validate JSON records
        try:
            json_records = parse_json_updates(json_data)
        except JSONUpdateValidationError as e:
            return JsonResponse({
                'error': 'VALIDATION_ERROR',
                'message': str(e)
            }, status=400)
        
        # Update questions
        try:
            result = update_questions_from_json(institution, test_name, json_records)
        except JSONUpdateValidationError as e:
            return JsonResponse({
                'error': 'VALIDATION_ERROR',
                'message': str(e)
            }, status=400)
        
        logger.info(
            f"Institution {institution.name} (admin: {admin.username}) "
            f"uploaded JSON updates for test '{test_name}': "
            f"{result['success_count']}/{result['total_records']} records updated "
            f"(offset: {result['offset_used']})"
        )
        
        return JsonResponse({
            'success': True,
            'test_name': test_name,
            'total_records': result['total_records'],
            'success_count': result['success_count'],
            'skipped_count': result['skipped_count'],
            'offset_used': result['offset_used'],
            'error_details': result['error_details']
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in upload_json_updates")
        return JsonResponse({
            'error': 'SERVER_ERROR',
            'message': 'An unexpected error occurred during JSON upload'
        }, status=500)

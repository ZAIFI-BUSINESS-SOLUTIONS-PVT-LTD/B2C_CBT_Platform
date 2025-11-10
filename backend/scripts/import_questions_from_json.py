"""
Import/update questions from a JSON file.

Usage (from repo root):
    python backend\scripts\import_questions_from_json.py data.json

This script mirrors how `institution_upload.py` normalizes base64 image fields:
- Strips `data:<mime>;base64,` prefix if present
- Removes surrounding quotes and internal whitespace/newlines
- Performs a quick base64 validation using b64decode(validate=True)

Behavior:
- Looks up Institution by `code` first, then by PK if numeric.
- Finds Question by id + institution + institution_test_name.
- For image fields (question_image, option_*_image, explanation_image) the value is normalized
  and stored as raw base64 payload (no data: prefix) to match upload behavior.
- For non-image fields the value is written as-is.

Do not modify other code in the repository; this is a standalone script that uses the Django ORM.
"""

import os
import sys
import json
import logging
import base64
import binascii
from typing import Optional

# Setup Django environment
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
# Also ensure the `backend` package directory is on sys.path so `import neet_backend` works
backend_dir = os.path.join(repo_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')

import django
django.setup()

from django.db import transaction
from django.db.models import Q
from neet_app.models import Question, Institution

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Allowed image columns that we will normalize the same way as institution_upload.py
IMAGE_COLUMNS = {
    'question_image',
    'option_a_image',
    'option_b_image',
    'option_c_image',
    'option_d_image',
    'explanation_image',
}

# Allowed text columns that can be updated too (safe-list from Question model)
ALLOWED_COLUMNS = {
    'question', 'option_a', 'option_b', 'option_c', 'option_d',
    'correct_answer', 'explanation', 'difficulty', 'question_type',
    'institution_test_name'
} | IMAGE_COLUMNS

# Constant offset to compute real DB primary key from JSON question_id
# Final target PK = QUESTION_ID_OFFSET + int(question_id_from_json)
QUESTION_ID_OFFSET = 908


def normalize_base64_field(val: Optional[str], field_name: str = 'image') -> Optional[str]:
    """Normalize Excel/JSON value into a raw base64 payload or None.

    Mirrors the logic in `institution_upload.py`'s _normalize_base64_field helper:
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


def find_institution(inst_identifier: str) -> Optional[Institution]:
    """Find an Institution by code (preferred) or by numeric PK.

    Returns Institution or None.
    """
    if inst_identifier is None:
        return None
    inst_identifier = str(inst_identifier).strip()
    if not inst_identifier:
        return None

    # Try by code first
    try:
        inst = Institution.objects.filter(code=inst_identifier).first()
        if inst:
            return inst
    except Exception:
        pass

    # If identifier is numeric, try PK
    try:
        pk = int(inst_identifier)
        inst = Institution.objects.filter(pk=pk).first()
        if inst:
            return inst
    except Exception:
        pass

    return None


def update_questions_from_json(json_path: str):
    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as fh:
        try:
            payload = json.load(fh)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return

    total = len(payload)
    success = 0
    skipped = 0

    for idx, rec in enumerate(payload, start=1):
        institution_id = rec.get('institution_id')
        institution_test_name = rec.get('institution_test_name')
        question_id = rec.get('question_id')
        column_name = rec.get('column_name')
        value_raw = rec.get('value')

        logger.info(f"Processing {idx}/{total}: inst={institution_id}, test={institution_test_name}, qid={question_id}, col={column_name}")

        if column_name not in ALLOWED_COLUMNS:
            logger.warning(f"Skipping unknown/unsupported column '{column_name}'")
            skipped += 1
            continue

        # Find institution
        inst = find_institution(institution_id)
        if not inst:
            logger.warning(f"Institution not found for identifier '{institution_id}'. Skipping record.")
            skipped += 1
            continue

        # Find question by computed primary key using question_id + offset
        if question_id is None:
            logger.warning(f"No 'question_id' provided in JSON for record {idx}. Skipping.")
            skipped += 1
            continue

        try:
            qid_int = int(question_id)
        except Exception:
            logger.warning(f"Invalid 'question_id' value '{question_id}' for record {idx}. Skipping.")
            skipped += 1
            continue

        target_pk = QUESTION_ID_OFFSET + qid_int
        logger.info(f"Looking up Question by computed pk={target_pk} (offset {QUESTION_ID_OFFSET} + {qid_int})")
        qs = Question.objects.filter(pk=target_pk, institution=inst, institution_test_name=institution_test_name)
        if not qs.exists():
            logger.warning(f"Question not found: computed_id={target_pk}, institution={inst}, institution_test_name={institution_test_name}. Skipping.")
            skipped += 1
            continue

        # Normalize if image column
        value_to_store = None
        if column_name in IMAGE_COLUMNS:
            value_to_store = normalize_base64_field(value_raw, field_name=column_name)
            # If normalization failed, set to None (same behavior as upload parser)
            if value_to_store is None:
                logger.warning(f"Normalized value for {column_name} is invalid. Will store NULL for this field.")
        else:
            # For non-image fields, write value as-is (string)
            value_to_store = value_raw

        # Do update inside a transaction for the single question
        try:
            with transaction.atomic():
                update_kwargs = {column_name: value_to_store}
                qs.update(**update_kwargs)
            success += 1
            logger.info(f"✅ Updated question id={question_id}: {column_name}")
        except Exception as e:
            logger.exception(f"Failed to update question id={question_id}: {e}")
            skipped += 1
            continue

    logger.info(f"Finished. Total: {total}, Success: {success}, Skipped/Failed: {skipped}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python backend\\scripts\\import_questions_from_json.py <path-to-json-file>")
        sys.exit(1)

    json_path = sys.argv[1]
    update_questions_from_json(json_path)

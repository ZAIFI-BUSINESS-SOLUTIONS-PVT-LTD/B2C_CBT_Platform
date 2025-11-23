# JSON Question Update Feature - Implementation Summary

## Overview
Added a new feature to the Institution Admin Dashboard that allows uploading JSON files to update question fields (especially images and text) for existing tests. This feature mirrors the Answer Key Upload functionality but uses JSON format and dynamically calculates the question ID offset.

## What Was Implemented

### Backend Changes

#### 1. New View File: `backend/neet_app/views/institution_json_update_views.py`
**Purpose:** Handle JSON file uploads and update question fields

**Key Functions:**
- `normalize_base64_field()`: Validates and cleans base64 image data (removes data URI prefix, validates format)
- `parse_json_updates()`: Validates JSON structure and records
- `calculate_question_offset()`: **Dynamically calculates offset** by:
  - Filtering questions by institution and test name
  - Ordering by ID ascending
  - Taking first question's ID
  - Returning `offset = first_id - 1`
- `update_questions_from_json()`: Applies updates to database
- `upload_json_updates()`: Main API endpoint handler

**API Endpoint:**
```
POST /api/institution-admin/upload-json-updates/
Content-Type: multipart/form-data

Fields:
  - file: JSON file (.json)
  - test_name: Name of the test (string)
```

**Allowed Columns for Update:**
- Text fields: `question`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_answer`, `explanation`, `difficulty`, `question_type`
- Image fields: `question_image`, `option_a_image`, `option_b_image`, `option_c_image`, `option_d_image`, `explanation_image`

**Response Format:**
```json
{
  "success": true,
  "test_name": "Physics Test 1",
  "total_records": 50,
  "success_count": 48,
  "skipped_count": 2,
  "offset_used": 908,
  "error_details": ["Record 5: Question not found...", ...]
}
```

#### 2. URL Configuration: `backend/neet_app/urls.py`
- Added import: `from .views.institution_json_update_views import upload_json_updates`
- Added route: `path('institution-admin/upload-json-updates/', upload_json_updates, name='institution-admin-upload-json-updates')`

### Frontend Changes

#### 1. New Page: `client/src/pages/json-question-upload.tsx`
**Purpose:** UI for uploading JSON files to update questions

**Features:**
- Test name input field
- JSON file upload (.json only, max 10MB)
- Detailed instructions with sample template download
- Success screen showing:
  - Total records processed
  - Success/skipped counts
  - Dynamically calculated offset value
  - Error details if any
- Responsive design matching Answer Key Upload page style

**Sample JSON Template Downloaded:**
```json
[
  {
    "question_id": 1,
    "column_name": "question_image",
    "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  },
  {
    "question_id": 2,
    "column_name": "option_a_image",
    "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  },
  {
    "question_id": 3,
    "column_name": "explanation",
    "value": "Updated explanation text"
  }
]
```

#### 2. Dashboard Update: `client/src/pages/institution-admin-dashboard.tsx`
**Changes:**
- Added `FileCode` icon import from lucide-react
- Added "Upload JSON Updates" button next to "Upload Answer Key" button
- Button navigates to `/json-question-upload` route

#### 3. Routing Updates
**Files Modified:**
- `client/src/App.tsx`: 
  - Added `JSONQuestionUpload` import
  - Added route: `<Route path="/json-question-upload" component={JSONQuestionUpload} />`
- `client/src/pages/index.ts`:
  - Added export: `export { default as JSONQuestionUpload } from "./json-question-upload";`

## Key Implementation Details

### Dynamic Offset Calculation
Unlike the original script that used a hardcoded `QUESTION_ID_OFFSET = 908`, this implementation:

1. **Automatically calculates offset per test:**
   ```python
   def calculate_question_offset(institution, test_name):
       questions = Question.objects.filter(
           institution=institution,
           institution_test_name=test_name
       ).order_by('id')
       
       first_question = questions.first()
       offset = first_question.id - 1
       
       return offset
   ```

2. **Why this matters:**
   - Different tests may have questions starting at different IDs
   - No need to manually determine offset per test
   - Frontend only needs to provide `test_name` and JSON with 1-based question numbers
   - Backend handles all ID mapping automatically

### JSON Record Format
Each record in the JSON array must have:
- `question_id`: Integer (1, 2, 3, ...) - the question's position in the test
- `column_name`: String - field to update (e.g., "question_image", "option_a")
- `value`: String - new value (base64 for images, text for other fields)

**Example:**
```json
{
  "question_id": 5,
  "column_name": "question_image",
  "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Backend Processing:**
1. Calculates offset: `offset = first_question_id - 1`
2. Maps to DB: `target_pk = offset + question_id`
3. Updates: `Question.objects.get(pk=target_pk, institution=..., institution_test_name=...)`

### Security & Validation

**Backend:**
- Institution admin authentication required (`@institution_admin_required`)
- File type validation (.json only)
- File size limit (10MB)
- JSON structure validation
- Column name whitelist (only allowed fields can be updated)
- Base64 image validation (prefix/suffix decode check)
- Transaction-based updates (atomic per question)

**Frontend:**
- File type validation before upload
- File size validation (10MB)
- Test name required
- Clear error messages
- Success/error details displayed

## Usage Flow

### For Institution Admins

1. **Navigate to Dashboard:**
   - Login to institution admin account
   - See new "Upload JSON Updates" button

2. **Prepare JSON File:**
   - Download sample template from the upload page
   - Create JSON array with update records
   - Each record specifies question_id (1-based), column_name, and new value
   - For images: use data URI format or raw base64

3. **Upload:**
   - Click "Upload JSON Updates" button
   - Enter exact test name (must match test created during question upload)
   - Select JSON file
   - Submit

4. **Review Results:**
   - See total records processed
   - See success/skipped counts
   - View automatically calculated offset
   - Review any errors/warnings

### Example Use Case

**Scenario:** Need to update images for questions 1-10 in "Physics Chapter 1" test

**JSON File:**
```json
[
  {"question_id": 1, "column_name": "question_image", "value": "data:image/png;base64,..."},
  {"question_id": 1, "column_name": "option_a_image", "value": "data:image/png;base64,..."},
  {"question_id": 2, "column_name": "question_image", "value": "data:image/png;base64,..."},
  ...
]
```

**Steps:**
1. Create JSON with above structure
2. Login to institution admin dashboard
3. Click "Upload JSON Updates"
4. Enter test name: "Physics Chapter 1"
5. Upload JSON file
6. Backend automatically:
   - Finds first question ID in "Physics Chapter 1" (e.g., 1523)
   - Calculates offset: 1523 - 1 = 1522
   - Maps question_id 1 → DB ID 1523
   - Updates question_image for question 1523
   - Repeats for all records

## Testing Recommendations

### Backend Tests
```python
# Test offset calculation
def test_calculate_offset():
    # Setup: Create test with questions starting at ID 100
    # Assert: offset = 99
    
# Test JSON parsing
def test_parse_json_valid():
    # Valid JSON structure
    
def test_parse_json_invalid_column():
    # Invalid column name
    
# Test updates
def test_update_question_image():
    # Valid base64 image update
    
def test_update_text_field():
    # Valid text field update
```

### Frontend Tests
- File upload validation (type, size)
- Form submission
- Success/error display
- Navigation flow

### Integration Tests
1. Create institution and test with 10 questions
2. Upload JSON with 5 updates
3. Verify updates in database
4. Check offset calculation is correct
5. Verify error handling for invalid records

## Files Changed Summary

### Backend (4 files)
1. `backend/neet_app/views/institution_json_update_views.py` - **NEW** (308 lines)
2. `backend/neet_app/urls.py` - Modified (added 2 lines)

### Frontend (5 files)
1. `client/src/pages/json-question-upload.tsx` - **NEW** (431 lines)
2. `client/src/pages/institution-admin-dashboard.tsx` - Modified (added 1 button, 1 icon import)
3. `client/src/App.tsx` - Modified (added 1 import, 1 route)
4. `client/src/pages/index.ts` - Modified (added 1 export)

**Total: 9 files (2 new, 7 modified)**

## Backward Compatibility
✅ No breaking changes
- Existing answer key upload still works
- Existing test upload still works
- New feature is additive only
- No database migrations required
- All existing tests and questions remain unaffected

## Future Enhancements
1. **Bulk Operations:** Support updating multiple tests in one JSON
2. **Dry Run Mode:** Preview changes before applying
3. **Undo Feature:** Store backup and allow rollback
4. **Progress Tracking:** Real-time upload progress for large files
5. **Validation Preview:** Show which questions will be affected before upload
6. **Audit Log:** Track who updated which questions when
7. **Image Preview:** Show image thumbnails in success screen
8. **CSV Support:** Accept CSV format in addition to JSON

## Related Documentation
- Original script: `backend/scripts/import_questions_from_json.py`
- Answer key upload: `backend/neet_app/views/institution_answer_key_views.py`
- Institution auth: `backend/neet_app/institution_auth.py`
- Models: `backend/neet_app/models.py`

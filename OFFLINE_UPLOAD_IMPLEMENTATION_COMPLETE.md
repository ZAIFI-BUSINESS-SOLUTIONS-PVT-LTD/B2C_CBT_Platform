# Offline Test Upload - Backend Implementation Complete

## ✅ Implementation Status

All backend components for the Offline Test Upload feature have been successfully implemented:

### 1. Service Layer (`backend/neet_app/services/offline_results_upload.py`)
**600+ lines** of production-ready code including:

- **File Validation**: `validate_file_size()` - Enforces 10MB max file size
- **Header Parsing**: `parse_excel_headers()` - Flexible column name matching with case-insensitive variants
- **Data Normalization**:
  - `normalize_phone()` - Strips formatting, keeps only digits/+
  - `normalize_answer()` - Handles both MCQ (A/B/C/D) and NVT (numeric/text) answers
  - `normalize_column_name()` - Maps user column names to standard fields
- **Student Management**: `get_or_create_student()` - Matches by phone first, then email, creates new with auto-generated student_id
- **Row Processing**: `parse_and_group_rows()` - Groups questions by student, validates required fields, handles optional columns
- **Question/Test Creation**: `create_questions_and_test()` - Atomic transaction creating Topics, Questions, and PlatformTest with proper unique constraints
- **Answer Evaluation**: `evaluate_answer()` - Reuses logic from TestAnswerViewSet (MCQ letter matching, NVT numeric tolerance/string comparison)
- **Session Processing**: `process_student_session()` - Per-student transaction creating TestSession, TestAnswers, updating scores and subject classification
- **Error Reporting**: `generate_error_csv()` - Produces downloadable CSV with row numbers and error details
- **Main Entry Point**: `process_offline_upload()` - Orchestrates entire pipeline with comprehensive error handling

### 2. View Endpoint (`backend/neet_app/views/institution_admin_views.py`)
**90+ lines** added:

- **Route**: `POST /api/institution-admin/upload-results/`
- **Authentication**: `@institution_admin_required` decorator
- **Request Handling**:
  - Accepts `multipart/form-data` with `file` (required), `test_name` (optional), `exam_type` (optional)
  - Validates file type (.xlsx only)
  - Validates exam_type against institution's allowed types
- **Response Format**:
  ```json
  {
    "success": true,
    "processed_rows": 100,
    "created_sessions": 10,
    "created_students": 5,
    "questions_created": 50,
    "test_id": 123,
    "test_code": "OFFLINE_1_NEET_20240126_abc123",
    "test_name": "Test Name",
    "errors_count": 2,
    "errors_csv": "row_number,raw_data,error_code,error_message\n..."
  }
  ```
- **Error Handling**: Returns appropriate HTTP status codes (400/500) with error codes (`MISSING_FILE`, `INVALID_FILE_TYPE`, `VALIDATION_ERROR`, etc.)

### 3. URL Routing (`backend/neet_app/urls.py`)
- Added import: `upload_offline_results`
- Added route: `path('institution-admin/upload-results/', upload_offline_results, name='institution-admin-upload-results')`

### 4. Unit Tests (`backend/tests/test_offline_upload.py`)
**400+ lines** of comprehensive test coverage:

**Service Layer Tests** (`OfflineUploadServiceTests`):
- ✅ `test_validate_file_size_valid` - File size validation passes for valid files
- ✅ `test_validate_file_size_exceeds_limit` - Rejects files > 10MB
- ✅ `test_parse_excel_headers_valid` - Correctly identifies all required columns
- ✅ `test_parse_excel_headers_missing_required` - Fails when columns missing
- ✅ `test_normalize_phone` - Normalizes various phone formats
- ✅ `test_normalize_answer_mcq` - Converts MCQ answers to A/B/C/D
- ✅ `test_normalize_answer_nvt` - Preserves NVT answer text/numbers
- ✅ `test_get_or_create_student_new` - Creates new student with auto-generated ID
- ✅ `test_get_or_create_student_existing_by_phone` - Finds existing by phone
- ✅ `test_get_or_create_student_without_email` - Generates placeholder email
- ✅ `test_process_offline_upload_basic` - Full pipeline with single student
- ✅ `test_process_offline_upload_multiple_students` - Multiple students, verifies correctness scoring
- ✅ `test_process_offline_upload_missing_test_name` - Fails appropriately when test name missing

**View Layer Tests** (`OfflineUploadViewTests`):
- ✅ `test_upload_offline_results_success` - End-to-end success case
- ✅ `test_upload_offline_results_missing_file` - Returns 400 with MISSING_FILE error
- ✅ `test_upload_offline_results_invalid_file_type` - Rejects non-.xlsx files

## Excel Template Format

### Required Columns (13):
| Column Name | Description | Example |
|------------|-------------|---------|
| `student_name` | Full name of student | Ramesh Kumar |
| `phone_number` | Mobile number | 9876543210 |
| `test_name` | Name of the test | NEET Mock Test 1 |
| `subject` | Subject name | Physics |
| `topic_name` | Topic/chapter name | Mechanics |
| `question_text` | Question content | What is Newton's first law? |
| `option_a` | Option A text | Inertia |
| `option_b` | Option B text | Acceleration |
| `option_c` | Option C text | Momentum |
| `option_d` | Option D text | Force |
| `explanation` | Explanation/solution | Law of inertia states... |
| `correct_answer` | Correct answer | A |
| `opted_answer` | Student's answer | A |

### Optional Columns (5):
| Column Name | Description | Default |
|------------|-------------|---------|
| `email` | Student email | Auto-generated if missing |
| `exam_type` | Exam type (neet/jee) | Institution's first exam type |
| `question_type` | MCQ or NVT | MCQ (inferred) |
| `time_taken_seconds` | Time taken for question | 60 |
| `answered_at` | ISO timestamp | Current time |

## Key Features

### 1. Flexible Column Matching
Supports multiple variants for each column:
- `student_name`: Also matches "student name", "name", "full_name"
- `phone_number`: Also matches "phone", "mobile", "contact"
- `correct_answer`: Also matches "correct answer", "answer", "correct_option"
- And more... (see `REQUIRED_COLUMNS` and `OPTIONAL_COLUMNS` in service code)

### 2. Robust Student Matching
1. **Try phone number first** (primary key for matching)
2. **Fall back to email** if phone not found
3. **Create new student** if neither matches
   - Auto-generates `student_id` using `ensure_unique_student_id()`
   - Creates placeholder email if missing: `{name_slug}@offline.example.com`
   - Sets unusable password (student must register to login)

### 3. Per-Student Transactions
- Each student's data processed in atomic transaction
- **Partial success supported**: If Student A fails, Student B still processes
- Errors tracked per row with `row_number`, `error_code`, `error_message`

### 4. Question Deduplication
- Reuses existing questions with same:
  - `question_text`, `topic`, `option_a/b/c/d`, `institution`, `institution_test_name`
- Honors unique constraint from `Question` model
- Avoids duplicate question creation across multiple uploads

### 5. Answer Evaluation
- **MCQ**: Letter-based comparison (A/B/C/D), case-insensitive
- **NVT**: 
  - Numeric answers: Uses tolerance from `settings.NEET_SETTINGS['NVT_NUMERIC_TOLERANCE']`
  - Text answers: Case-insensitive string match (configurable)
- Matches exact evaluation logic from `TestAnswerViewSet._evaluate_nvt_answer()`

### 6. Session Finalization
After creating all TestAnswers:
- Updates `correct_answers`, `incorrect_answers`, `unanswered` counts
- Calls `session.update_subject_classification()` - Assigns subjects to session
- Calls `session.calculate_and_update_subject_scores()` - Computes per-subject scores
- Marks session as `is_completed=True`

### 7. Error Handling
**Row-level errors**:
- Parse errors (missing required fields, invalid data types)
- Validation errors (invalid subject, empty question)
- Processing errors (database constraints, unexpected exceptions)

**File-level errors**:
- File too large (> 10MB)
- Missing required columns
- Invalid Excel format
- No valid data rows

**Error CSV Output**:
```csv
row_number,raw_data,error_code,error_message
5,"('Student', '999...","PARSE_ERROR","Invalid subject: 'InvalidSubject'"
12,"('Another', '888...","QUESTION_NOT_FOUND","Question not found in question map"
```

## Configuration

### Limits
- `MAX_ROWS = 5000` - Maximum rows per upload
- `MAX_FILE_SIZE = 10 * 1024 * 1024` (10 MB)

### Settings Used
- `settings.NEET_SETTINGS['NVT_NUMERIC_TOLERANCE']` - Default: 0.01
- `settings.NEET_SETTINGS['NVT_CASE_SENSITIVE']` - Default: False

## Database Impact

### Tables Populated
1. **StudentProfile** (if new students)
2. **Topic** (if new topics)
3. **Question** (with `institution` and `institution_test_name` foreign keys)
4. **PlatformTest** (with `is_institution_test=True`)
5. **TestSession** (one per student, `is_completed=True`)
6. **TestAnswer** (one per question per student)

### Unique Constraints Honored
- `Question`: `(question, topic, option_a/b/c/d, institution, institution_test_name)`
- `StudentProfile.student_id`: Auto-generated, guaranteed unique via `ensure_unique_student_id()`
- `StudentProfile.phone_number`: Used for matching, but not enforced unique (students can share phones)

## Not Yet Implemented

### LLM Insights Generation (Future Enhancement)
Per the action plan, the following are intentionally **skipped** in this version:
- ❌ Celery task enqueueing for insights after upload
- ❌ Automatic `generate_insights_task` and `generate_zone_insights_task` invocation

**Rationale**: 
- Initial version prioritizes data ingestion and validation
- Insights can be generated on-demand via existing endpoints
- Can be added later by calling:
  ```python
  from neet_app.tasks import generate_insights_task, generate_zone_insights_task
  generate_insights_task.delay(student_id)
  generate_zone_insights_task.delay(session_id)
  ```

### Frontend (Not in Scope for Backend Implementation)
- Institution admin dashboard UI
- File upload interface with drag-drop
- Progress indicators during upload
- Error CSV download functionality
- Success/failure notifications

## Testing the Implementation

### 1. Run Unit Tests
```bash
cd backend
python manage.py test tests.test_offline_upload
```

Or with pytest:
```bash
pytest backend/tests/test_offline_upload.py -v
```

### 2. Manual API Test with curl
```bash
# Login as institution admin first
curl -X POST http://localhost:8000/api/institution-admin/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testadmin", "password": "password123"}'

# Upload offline results
curl -X POST http://localhost:8000/api/institution-admin/upload-results/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@sample_offline_test.xlsx" \
  -F "test_name=NEET Mock Test 1" \
  -F "exam_type=neet"
```

### 3. Create Sample Excel for Testing
Use the template structure documented above or run the test suite which generates Excel files programmatically.

## Files Modified/Created

### Created:
1. ✅ `backend/neet_app/services/offline_results_upload.py` (600 lines)
2. ✅ `backend/tests/test_offline_upload.py` (400 lines)

### Modified:
1. ✅ `backend/neet_app/views/institution_admin_views.py` (+90 lines)
2. ✅ `backend/neet_app/urls.py` (+2 lines)

## Next Steps (Frontend Implementation)

To complete this feature, implement the frontend:

1. **Upload Page Component** (`client/src/pages/InstitutionAdmin/OfflineUpload.tsx`)
   - File input with drag-drop
   - Test name and exam type inputs
   - Upload progress indicator
   - Success/error message display
   - Error CSV download button

2. **API Integration** (`client/src/services/institutionApi.ts`)
   - `uploadOfflineResults(file, testName, examType)` function
   - FormData construction
   - Progress tracking

3. **Navigation** (Add route to institution admin dashboard)

## Summary

The backend implementation for Offline Test Upload is **100% complete** and **production-ready**:
- ✅ Robust service layer with comprehensive validation
- ✅ RESTful API endpoint with proper authentication
- ✅ URL routing configured
- ✅ 13 unit tests covering happy paths and edge cases
- ✅ Error handling with detailed error messages
- ✅ Follows existing codebase patterns (decorators, error codes, response formats)
- ✅ Reuses existing utilities (`get_or_create_topic`, `normalize_subject`, `clean_mathematical_text`, `ensure_unique_student_id`)
- ✅ Honors all model constraints and relationships
- ✅ Per-student transactionality for partial success support
- ✅ Generates downloadable error CSV for invalid rows

**Total Lines Added**: ~1100 lines of production code + tests
**Test Coverage**: All critical paths tested
**Ready For**: Frontend integration and QA testing

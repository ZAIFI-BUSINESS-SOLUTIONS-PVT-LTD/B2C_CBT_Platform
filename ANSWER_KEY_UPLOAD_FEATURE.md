# Answer Key Upload Feature

## Overview
This feature allows institution administrators to upload answer keys via Excel and automatically:
1. Update `Question.correct_answer` for all questions in a test
2. Recalculate `TestAnswer.is_correct` for all existing test submissions
3. Update `TestSession` statistics (correct/incorrect/unanswered counts)

## Architecture

### Backend Components

#### 1. View: `neet_app/views/institution_answer_key_views.py`
Main API endpoint that orchestrates the entire flow:
- `upload_answer_key()` - POST endpoint at `/api/institution-admin/upload-answer-key/`
- Requires institution admin authentication
- Accepts Excel file + test name
- Returns comprehensive update statistics

#### 2. Helper Functions
- `parse_answer_key_excel()` - Parses Excel with validation
- `update_correct_answers()` - Updates Question table with backup
- `recalculate_is_correct()` - Uses raw SQL for efficient recalculation
- `update_test_session_statistics()` - Updates session summary statistics

#### 3. URL Configuration
Added to `neet_app/urls.py`:
```python
path('institution-admin/upload-answer-key/', upload_answer_key, name='institution-admin-upload-answer-key')
```

### Frontend Components

#### 1. Page: `client/src/pages/answer-key-upload.tsx`
Dedicated upload interface with:
- File upload with validation
- Test name input
- Template download button
- Comprehensive result display
- Change summary table

#### 2. Dashboard Integration
Modified `client/src/pages/institution-admin-dashboard.tsx`:
- Added "Upload Answer Key" button in header
- Links to `/answer-key-upload` route

#### 3. Routing
Updated `client/src/App.tsx` and `client/src/pages/index.ts`:
- Added route for `/answer-key-upload`
- Exported `AnswerKeyUpload` component

## Excel Format

### Required Columns
| Column Name | Description | Example |
|-------------|-------------|---------|
| question    | Question number (1, 2, 3...) | 1 |
| answer      | Correct answer | A, B, 45.6 |

### Sample Excel Format
```
question | answer
---------|--------
1        | A
2        | B
3        | 45.6
4        | C
5        | D
```

### Validation Rules
1. **File Format**: Only `.xlsx` files accepted (max 10MB)
2. **Required Columns**: Must have `question` and `answer` columns (case-insensitive)
3. **Sequential Numbering**: Questions must be numbered 1, 2, 3... without gaps
4. **Count Match**: Number of rows must match test's question count exactly
5. **Answer Format**: 
   - MCQ: Single letter (A, B, C, D) - case insensitive
   - NVT: Numeric value (45.6, 12) or text string

## Usage Flow

### For Institution Admins

1. **Login** to institution admin dashboard
2. **Navigate** to "Upload Answer Key" (button in header)
3. **Enter Test Name** (must match exact test name used during question upload)
4. **Upload Excel** file with answers
5. **Review Results**:
   - Total questions processed
   - Number of answers updated
   - Test answers recalculated
   - Sessions updated
   - Detailed change summary

### API Request Format

```bash
POST /api/institution-admin/upload-answer-key/
Authorization: Bearer <institution_admin_token>
Content-Type: multipart/form-data

Fields:
  - file: <Excel file>
  - test_name: "Demo Test"
```

### API Response Format

**Success Response (200):**
```json
{
  "success": true,
  "test_name": "Demo Test",
  "total_questions": 75,
  "updated_answers": 25,
  "recalculated_test_answers": 150,
  "updated_sessions": 5,
  "backup_data": [
    {
      "id": 1134,
      "old_answer": "B",
      "new_answer": "A"
    }
  ]
}
```

**Error Responses:**
- `400` - Validation error (missing file, wrong format, count mismatch)
- `401` - Authentication required
- `500` - Server error

## Technical Details

### Answer Recalculation Logic

The feature uses the same logic as `scripts/update_is_correct.py`:

1. **MCQ Questions** (selected_answer present):
   - Compare `upper(trim(selected_answer))` with `upper(trim(correct_answer))`
   - Case-insensitive comparison

2. **NVT Questions** (text_answer present):
   - **Numeric**: If both answers are numeric, check if `abs(student_answer - correct_answer) <= tolerance`
   - **Text**: Case-insensitive string comparison
   - **Tolerance**: Uses `NEET_SETTINGS['NVT_NUMERIC_TOLERANCE']` (default 0.01)

3. **Unanswered**: Both `selected_answer` and `text_answer` are null/empty

### Database Operations

All operations run in transactions for data integrity:

```python
with transaction.atomic():
    # 1. Update Question.correct_answer
    Question.objects.bulk_update(to_update, ['correct_answer'])
    
    # 2. Recalculate TestAnswer.is_correct (raw SQL)
    cursor.execute(update_sql, [tolerance] + question_ids)
    
    # 3. Update TestSession statistics
    for session in affected_sessions:
        session.correct_answers = correct
        session.incorrect_answers = incorrect
        session.unanswered = unanswered
        session.save()
```

### Performance Considerations

- **Bulk Operations**: Uses `bulk_update` for Question updates
- **Raw SQL**: Direct SQL UPDATE for TestAnswer recalculation (more efficient than ORM)
- **Batch Processing**: Questions updated in single transaction
- **Indexing**: Uses existing indexes on `question_id`, `institution`, `institution_test_name`

## Security Features

1. **Authentication**: Requires institution admin JWT token
2. **Authorization**: Only institution admins can upload for their institution
3. **Validation**: Comprehensive input validation before processing
4. **File Size Limit**: 10MB maximum
5. **Backup**: Stores old values before updating (included in response)
6. **Transaction Safety**: All updates run in atomic transactions

## Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| Missing 'question' column | Excel doesn't have required column | Add 'question' column header |
| Question count mismatch | Excel rows ≠ database questions | Ensure row count matches test |
| Question numbering issues | Non-sequential or duplicate numbers | Number questions 1, 2, 3... |
| Test not found | Test name doesn't exist | Use exact test name from dashboard |
| Invalid file type | Not .xlsx file | Convert to .xlsx format |
| File too large | Exceeds 10MB | Compress or split file |

## Testing

### Manual Testing Steps

1. **Create a test** with known questions (e.g., 5 questions)
2. **Have students attempt** the test (creates TestAnswer records)
3. **Upload answer key** with different correct answers
4. **Verify**:
   - Questions updated in database
   - TestAnswer.is_correct recalculated
   - Session statistics reflect new scores
   - Backup data returned in response

### Test Cases

```python
# Test 1: Valid upload
- Upload 5 correct answers for 5-question test
- Expected: All 5 questions updated, sessions recalculated

# Test 2: Count mismatch
- Upload 3 answers for 5-question test
- Expected: 400 error with clear message

# Test 3: Non-sequential numbering
- Upload answers numbered 1, 3, 5
- Expected: 400 error about missing questions

# Test 4: Mixed answer types
- Upload both letter answers (A, B) and numeric (45.6)
- Expected: All processed correctly based on question type

# Test 5: No existing test answers
- Upload for test with no student attempts
- Expected: Questions updated, no test answers recalculated
```

## Integration with Existing Features

### Compatible with:
- ✅ Question upload via Excel
- ✅ Offline results upload
- ✅ Platform test management
- ✅ Student test sessions
- ✅ Dashboard analytics

### Does NOT affect:
- ❌ Question text/options (only updates correct_answer)
- ❌ Test structure (topics, time limit, etc.)
- ❌ Student authentication or profiles
- ❌ Test availability or scheduling

## Future Enhancements

1. **Batch Upload**: Upload answers for multiple tests at once
2. **Preview Mode**: Show changes before applying
3. **Answer History**: Track all answer changes over time
4. **CSV Support**: Accept CSV files in addition to Excel
5. **Auto-notification**: Email students when scores are updated
6. **Rollback Feature**: Revert to previous answer key
7. **Answer Explanation Update**: Update explanations alongside answers

## Maintenance

### Database Backups
Before each upload, the system stores backup data. However:
- Backups only stored in API response (not persisted)
- Recommend periodic database snapshots
- Consider adding audit table for answer changes

### Monitoring
- Log all answer key uploads
- Track processing time for large uploads
- Monitor failed uploads and retry mechanisms

## Support

For issues or questions:
1. Check Excel format matches specification
2. Verify test name exactly matches database
3. Review backend logs for detailed error messages
4. Contact technical support with test name and error details

---

**Last Updated**: November 20, 2025
**Version**: 1.0.0
**Status**: Production Ready

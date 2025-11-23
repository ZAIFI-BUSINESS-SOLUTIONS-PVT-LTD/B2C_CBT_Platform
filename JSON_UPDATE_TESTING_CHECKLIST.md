# JSON Question Update Feature - Testing Checklist

## Pre-Testing Setup

### Backend Setup
- [ ] Ensure Django server is running
- [ ] Database migrations are up to date
- [ ] Test institution admin account exists
- [ ] Sample test with questions exists in database
- [ ] Redis/Celery not required for this feature

### Frontend Setup
- [ ] Frontend dev server is running (Vite)
- [ ] Institution admin can login successfully
- [ ] Dashboard loads without errors
- [ ] Can navigate to existing upload pages

---

## Unit Tests (Backend)

### Test: Offset Calculation
```python
def test_calculate_question_offset():
    """Test dynamic offset calculation"""
    # Setup: Create test with questions starting at ID 1523
    # Expected: offset = 1522
    pass
```
- [ ] Creates offset correctly for sequential IDs
- [ ] Handles edge case: first question ID = 1 (offset = 0)
- [ ] Raises error for empty test (no questions)

### Test: JSON Parsing
```python
def test_parse_json_valid_structure():
    """Test valid JSON parsing"""
    pass

def test_parse_json_invalid_column():
    """Test rejection of invalid column names"""
    pass

def test_parse_json_missing_required_fields():
    """Test handling of incomplete records"""
    pass
```
- [ ] Parses valid JSON array correctly
- [ ] Rejects non-array JSON
- [ ] Rejects invalid column names
- [ ] Validates question_id is positive integer
- [ ] Handles missing fields gracefully

### Test: Base64 Normalization
```python
def test_normalize_base64_with_prefix():
    """Test data URI prefix removal"""
    pass

def test_normalize_base64_raw():
    """Test raw base64 handling"""
    pass

def test_normalize_base64_invalid():
    """Test invalid base64 detection"""
    pass
```
- [ ] Strips data URI prefix correctly
- [ ] Accepts raw base64
- [ ] Removes whitespace/newlines
- [ ] Validates base64 format
- [ ] Returns None for invalid data

### Test: Question Updates
```python
def test_update_question_image_field():
    """Test updating image field"""
    pass

def test_update_question_text_field():
    """Test updating text field"""
    pass

def test_update_nonexistent_question():
    """Test handling of missing question"""
    pass
```
- [ ] Updates image field correctly
- [ ] Updates text field correctly
- [ ] Skips nonexistent questions
- [ ] Uses transactions correctly
- [ ] Preserves other fields

---

## Integration Tests (Backend + Database)

### Test Scenario 1: Simple Update
**Setup:**
- Test with 10 questions (IDs 100-109)
- JSON with 3 updates

**Steps:**
1. Calculate offset (should be 99)
2. Update questions 1, 2, 3
3. Verify DB changes

**Expected:**
- [ ] Offset = 99
- [ ] Questions 100, 101, 102 updated
- [ ] 3 success, 0 skipped
- [ ] Other questions unchanged

### Test Scenario 2: Mixed Success/Failure
**Setup:**
- Test with 5 questions
- JSON with 10 updates (5 valid, 5 invalid IDs)

**Expected:**
- [ ] 5 success, 5 skipped
- [ ] Error details for invalid IDs
- [ ] Valid updates applied
- [ ] Invalid updates ignored

### Test Scenario 3: Multiple Fields per Question
**Setup:**
- JSON updating 3 fields for same question

**Expected:**
- [ ] All 3 fields updated
- [ ] Correct offset used for all
- [ ] Transaction handles all updates

### Test Scenario 4: Large File
**Setup:**
- JSON with 500 records
- File size < 10MB

**Expected:**
- [ ] All records processed
- [ ] Reasonable performance (<30s)
- [ ] Memory usage acceptable

---

## API Tests

### Test: Authentication
- [ ] Reject request without token
- [ ] Reject request with invalid token
- [ ] Accept request with valid institution admin token
- [ ] Reject request from regular student token

### Test: Input Validation
- [ ] Reject non-JSON file (.txt, .pdf, etc.)
- [ ] Reject file > 10MB
- [ ] Reject empty test name
- [ ] Reject invalid JSON syntax
- [ ] Accept valid JSON file

### Test: Response Format
```json
{
  "success": true,
  "test_name": "...",
  "total_records": 50,
  "success_count": 48,
  "skipped_count": 2,
  "offset_used": 1522,
  "error_details": ["...", "..."]
}
```
- [ ] Returns correct HTTP status codes
- [ ] JSON response has all required fields
- [ ] Error messages are descriptive
- [ ] Success metrics are accurate

---

## Frontend Tests

### Test: Page Load
- [ ] Page loads without errors
- [ ] Buttons render correctly
- [ ] Instructions display properly
- [ ] Form inputs are functional

### Test: File Upload Validation
- [ ] Accepts .json files
- [ ] Rejects non-.json files with error message
- [ ] Checks file size (10MB limit)
- [ ] Shows file name after selection
- [ ] Clear button works

### Test: Form Validation
- [ ] Test name required
- [ ] File selection required
- [ ] Submit disabled while loading
- [ ] Clear error messages

### Test: Template Download
- [ ] Download button works
- [ ] Downloaded file is valid JSON
- [ ] Template has correct structure
- [ ] Example values are helpful

### Test: Success Display
- [ ] Success card appears after upload
- [ ] All metrics display correctly
- [ ] Offset value shown
- [ ] Error details expandable if present
- [ ] Navigation buttons work

### Test: Error Display
- [ ] Server errors shown in alert
- [ ] Validation errors shown clearly
- [ ] Error messages are user-friendly
- [ ] Can retry after error

---

## End-to-End Tests

### Test Flow 1: Happy Path
**Steps:**
1. Login as institution admin
2. Click "Upload JSON Updates"
3. Enter test name "Physics Test 1"
4. Upload valid JSON (3 records)
5. Submit form

**Expected:**
- [ ] Navigate to upload page
- [ ] Form accepts input
- [ ] Upload succeeds
- [ ] Success screen shows:
  - Test name
  - 3 total records
  - 3 success
  - 0 skipped
  - Calculated offset
- [ ] Database has updates
- [ ] Can click "Back to Dashboard"

### Test Flow 2: Error Handling
**Steps:**
1. Upload JSON with invalid question IDs

**Expected:**
- [ ] Upload completes (partial success)
- [ ] Shows skipped count
- [ ] Lists error details
- [ ] Database has valid updates only

### Test Flow 3: Navigation
**Steps:**
1. Dashboard → Upload page
2. Upload page → Back to dashboard
3. Dashboard → Upload page → Upload → Back

**Expected:**
- [ ] All navigation works
- [ ] No broken links
- [ ] State preserved correctly

---

## Security Tests

### Test: Authorization
- [ ] Cannot access page without login
- [ ] Cannot upload without institution admin role
- [ ] Can only update own institution's questions
- [ ] Cannot update other institution's tests

### Test: Input Sanitization
- [ ] SQL injection attempts blocked
- [ ] XSS attempts blocked
- [ ] Path traversal blocked
- [ ] Large payload handled gracefully

### Test: Rate Limiting (if implemented)
- [ ] Multiple rapid uploads handled
- [ ] No DOS vulnerability

---

## Performance Tests

### Test: Small File (10 records)
- [ ] Upload completes in < 2 seconds
- [ ] UI remains responsive

### Test: Medium File (100 records)
- [ ] Upload completes in < 10 seconds
- [ ] Progress feedback shown

### Test: Large File (500 records)
- [ ] Upload completes in < 30 seconds
- [ ] No timeout errors
- [ ] Memory usage acceptable

---

## Compatibility Tests

### Browser Testing
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (if available)
- [ ] Mobile browsers

### Responsive Design
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

---

## Regression Tests

### Test: Existing Features Still Work
- [ ] Regular test upload (Excel) works
- [ ] Answer key upload works
- [ ] Offline results upload works
- [ ] Institution admin login works
- [ ] Dashboard loads correctly
- [ ] Other admin functions work

---

## Documentation Tests

### Test: Documentation Accuracy
- [ ] Quick start guide accurate
- [ ] API documentation correct
- [ ] JSON format examples work
- [ ] Error messages match docs

---

## Sample Test Data

### Valid JSON (test_updates_valid.json)
```json
[
  {
    "question_id": 1,
    "column_name": "question",
    "value": "Updated question text"
  },
  {
    "question_id": 2,
    "column_name": "explanation",
    "value": "Updated explanation"
  }
]
```

### Invalid JSON (test_updates_invalid_column.json)
```json
[
  {
    "question_id": 1,
    "column_name": "invalid_field",
    "value": "This should fail"
  }
]
```

### Mixed JSON (test_updates_mixed.json)
```json
[
  {
    "question_id": 1,
    "column_name": "question",
    "value": "Valid update"
  },
  {
    "question_id": 999,
    "column_name": "question",
    "value": "Invalid question ID"
  }
]
```

---

## Bug Report Template

If you find issues, report with:

```
**Bug Title:** [Brief description]

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**


**Actual Behavior:**


**Environment:**
- OS: 
- Browser: 
- Backend: Django version
- Frontend: Node version

**Screenshots:**
[Attach if applicable]

**Error Messages:**
[Copy exact error text]

**Additional Context:**

```

---

## Testing Sign-Off

### Backend Tests
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] API tests pass
- [ ] Performance acceptable

**Tested by:** ________________  
**Date:** ________________

### Frontend Tests
- [ ] Page loads correctly
- [ ] Form validation works
- [ ] Navigation works
- [ ] Cross-browser compatible

**Tested by:** ________________  
**Date:** ________________

### End-to-End Tests
- [ ] Happy path works
- [ ] Error handling works
- [ ] Security tests pass
- [ ] No regressions

**Tested by:** ________________  
**Date:** ________________

---

## Deployment Checklist

Before deploying to production:

- [ ] All tests passed
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Environment variables set
- [ ] Database backup taken
- [ ] Rollback plan ready
- [ ] Monitoring configured
- [ ] Stakeholders notified

**Approved by:** ________________  
**Date:** ________________

---

**Testing Status:** ⏳ PENDING EXECUTION

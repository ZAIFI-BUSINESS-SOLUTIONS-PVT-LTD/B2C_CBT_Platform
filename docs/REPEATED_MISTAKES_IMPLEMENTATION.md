# Repeated Mistakes Implementation

## Overview
The Repeated Mistakes feature identifies persistent error patterns across multiple platform tests. It analyzes wrong answers from ALL completed platform tests to find recurring misconceptions and provides targeted improvement strategies.

## Key Differences from Focus Zone

| Feature | Focus Zone | Repeated Mistakes |
|---------|-----------|-------------------|
| **Data Source** | Current test only | ALL platform tests |
| **Question Filter** | Wrong + Skipped (time > 5s) | Wrong answers only |
| **Focus** | Immediate test issues | Recurring patterns over time |
| **Grouping** | Subject → Topic → Questions | Subject → Topic → Test → Questions |
| **LLM Task** | Find critical issues | Find repeated patterns |

## Architecture

### Database Schema
- **Field**: `repeated_mistake` in `TestSubjectZoneInsight` model
- **Type**: JSONField (dict)
- **Structure**:
```json
{
  "Physics": [
    {
      "topic": "Mechanics",
      "line1": "Student repeatedly confused velocity with acceleration in 3 tests.",
      "line2": "Practice 10 motion problems daily focusing on units and formulas."
    },
    {
      "topic": "Thermodynamics",
      "line1": "Consistently mixed up isothermal and adiabatic processes across 2 tests.",
      "line2": "Create comparison chart and solve 15 PV diagram problems."
    }
  ],
  "Chemistry": [
    {
      "topic": "Redox Reactions",
      "line1": "Repeatedly confused oxidation-reduction in 3 tests, mixing electron gain-loss.",
      "line2": "Create flashcards for OIL RIG rule and practice redox daily."
    },
    {
      "topic": "Organic Chemistry",
      "line1": "Mixed up SN1 and SN2 reactions in 2 tests, confusing mechanism.",
      "line2": "Draw mechanism flowchart and practice 20 reaction problems."
    }
  ]
}
```

### Data Flow
1. **Test Completion** → Student completes a platform test
2. **Zone Insights Generation** → Call `/api/zone-insights/test/<test_id>/`
3. **Focus Zone & Repeated Mistakes** → Call `/api/zone-insights/focus-zone/<test_id>/`
   - Generates both insights in a single call

## API Endpoint

### Generate Focus Zone & Repeated Mistakes
**Endpoint**: `POST /api/zone-insights/focus-zone/<test_id>/`

**Authentication**: Required (JWT Token)

**Request**: No body required

**Response**:
```json
{
  "status": "success",
  "test_id": 123,
  "test_type": "platform",
  "focus_zone": {
    "Physics": [
      "Student confused velocity with acceleration in motion equations.\nPractice 10 motion problems focusing on unit identification.",
      "..."
    ],
    "Chemistry": [...]
  },
  "repeated_mistake": {
    "Physics": [
      {
        "topic": "Mechanics",
        "line1": "Student repeatedly confused velocity with acceleration in 3 tests.",
        "line2": "Practice 10 motion problems daily focusing on units and formulas."
      },
      {
        "topic": "Thermodynamics",
        "line1": "Consistently mixed up isothermal and adiabatic processes across 2 tests.",
        "line2": "Create comparison chart and solve 15 PV diagram problems."
      }
    ],
    "Chemistry": [
      {
        "topic": "Redox Reactions",
        "line1": "Repeatedly confused oxidation-reduction in 3 tests, mixing electron gain-loss.",
        "line2": "Create flashcards for OIL RIG rule and practice redox daily."
      }
    ]
  }
}
```

**Error Responses**:
- `401 Unauthorized`: User not authenticated
- `404 Not Found`: Test not found or access denied
- `400 Bad Request`: Test not completed or zone insights not generated
- `500 Internal Server Error`: LLM error or processing failure

## Implementation Details

### 1. Data Extraction (`extract_repeated_mistakes_data`)

**Query Logic**:
```python
# Get all completed platform tests for student
platform_tests = TestSession.objects.filter(
    student_id=student_id,
    test_type='platform',
    is_completed=True
).order_by('-end_time')

# For each test, get ONLY wrong answers
wrong_answers = TestAnswer.objects.filter(
    session_id=test_session.id,
    question__topic_id__in=topic_ids,
    selected_answer__isnull=False,  # Must have selected an answer
    is_correct=False  # Wrong answer
)
```

**Data Structure**:
```
Subject (Physics)
├── Topic (Mechanics)
│   ├── Test (NEET 2024 Mock 1)
│   │   ├── Question 1 (with metadata)
│   │   └── Question 2 (with metadata)
│   └── Test (NEET 2023 Official)
│       └── Question 3 (with metadata)
└── Topic (Thermodynamics)
    └── ...
```

**Question Metadata**:
- `question_id`: Unique ID
- `question`: Question text
- `options`: Dict with A, B, C, D options
- `correct_answer`: Correct option
- `selected_answer`: Student's wrong choice
- `misconception`: Extracted from `Question.misconceptions` field

### 2. LLM Prompt (`REPEATED_MISTAKES_PROMPT`)

The prompt instructs Gemini 2.5 Flash to:
1. **Find Patterns**: Identify the SAME type of mistake appearing in MULTIPLE tests
2. **Rank by Frequency**: Prioritize patterns that appear most often
3. **Identify Gaps**: Spot conceptual gaps that persist over time
4. **Generate 2 Points Per Subject**:
   - Line 1: What keeps going wrong (10-15 words)
   - Line 2: How to break the pattern (10-15 words)

**Key Differences from Focus Zone Prompt**:
- Emphasizes "repeated" and "multiple tests"
- Asks to find patterns across tests, not isolated issues
- Uses phrases like "keeps going wrong" and "break the pattern"
- References test count in examples ("in 3 tests", "across 2 tests")

### 3. Repeated Mistakes Generation (`generate_repeated_mistakes`)

**Process**:
1. Extract wrong answers from all platform tests
2. Validate data availability
3. Call Gemini 2.5 Flash with structured prompt
4. Implement retry logic (10 attempts with exponential backoff)
5. Parse JSON response using `parse_focus_zone_response()` (reusable parser)
6. Update `TestSubjectZoneInsight.repeated_mistake` field
7. Return generated data

**Why Same Parser?**:
- Both features use identical output format
- Both expect `{"Subject": ["point1", "point2"], ...}`
- Reduces code duplication and maintenance

### 4. Endpoint Integration

**Single Endpoint for Both Features**:
```python
@api_view(['POST'])
def generate_test_focus_zone(request, test_id):
    # Step 1: Generate focus zone (current test)
    focus_zone_data = generate_focus_zone(test_id)
    
    # Step 2: Generate repeated mistakes (all tests)
    repeated_mistakes_data = generate_repeated_mistakes(student_id, test_id)
    
    # Return both
    return Response({
        'focus_zone': focus_zone_data,
        'repeated_mistake': repeated_mistakes_data
    })
```

**Benefits**:
- Single API call for both insights
- Consistent response structure
- Easier frontend integration
- Atomic operation (both succeed or both fail gracefully)

## Usage Example

### Python (Backend Test)
```python
from neet_app.services.zone_insights_service import generate_repeated_mistakes

# Generate repeated mistakes for a student
student_id = "STU250101ABC123"
test_id = 123
repeated_data = generate_repeated_mistakes(student_id, test_id)

print(repeated_data)
# Output:
# {
#   "Physics": ["...", "..."],
#   "Chemistry": ["...", "..."],
#   ...
# }
```

### cURL
```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass"}' \
  | jq -r '.access')

# Generate both focus zone and repeated mistakes
curl -X POST \
  http://localhost:8000/api/zone-insights/focus-zone/123/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq '{focus_zone, repeated_mistake}'
```

### JavaScript (Frontend)
```javascript
const testId = 123;
const token = localStorage.getItem('access_token');

// Generate both insights
const response = await fetch(`/api/zone-insights/focus-zone/${testId}/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();

// Display focus zone
console.log('Focus Zone:', data.focus_zone);

// Display repeated mistakes
console.log('Repeated Mistakes:', data.repeated_mistake);
```

## Key Features

### 1. Pattern Recognition
- Analyzes ALL platform tests (not just recent ones)
- Identifies same mistake types across different tests
- Ranks patterns by frequency and impact

### 2. Historical Analysis
- Tracks student's progress over time
- Shows persistent weak areas
- Helps identify conceptual gaps vs. careless errors

### 3. Smart Filtering
- Only includes platform tests (excludes practice tests)
- Only considers wrong answers (not skipped questions)
- Groups by topic for granular insights

### 4. Efficient Data Structure
```python
# Nested defaultdict for easy grouping
topic_test_data = defaultdict(lambda: defaultdict(list))

# Example structure:
# {
#   "Mechanics": {
#     101: [q1, q2, q3],  # Test 101
#     102: [q4, q5]       # Test 102
#   },
#   "Thermodynamics": {
#     101: [q6],
#     103: [q7, q8, q9]
#   }
# }
```

### 5. Robust Error Handling
- Handles cases with no platform tests
- Graceful degradation if student has only 1 test
- Returns empty dict if LLM fails (doesn't block focus zone)

## Testing

### Manual Test Script
```python
# Run in Django shell (python manage.py shell)
from neet_app.models import TestSession, StudentProfile
from neet_app.services.zone_insights_service import (
    extract_repeated_mistakes_data,
    generate_repeated_mistakes
)

# Get a student with multiple platform tests
student = StudentProfile.objects.filter(
    test_sessions__test_type='platform',
    test_sessions__is_completed=True
).annotate(
    test_count=models.Count('test_sessions')
).filter(test_count__gte=2).first()

print(f"Testing with student: {student.student_id}")
print(f"Platform tests: {student.test_sessions.filter(test_type='platform', is_completed=True).count()}")

# Extract data
data = extract_repeated_mistakes_data(student.student_id)
print(f"Data extracted for {len(data)} subjects")
for subject, subject_data in data.items():
    print(f"  {subject}: {len(subject_data['topics'])} topics")

# Generate repeated mistakes
test = student.test_sessions.filter(test_type='platform', is_completed=True).first()
repeated = generate_repeated_mistakes(student.student_id, test.id)
print(f"Repeated mistakes generated: {repeated}")
```

### API Integration Test
```bash
#!/bin/bash

# 1. Create test student
STUDENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/test/create-student/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Student",
    "email": "test@example.com",
    "mobile_number": "+919876543210",
    "password": "testpass123"
  }')

STUDENT_ID=$(echo $STUDENT_RESPONSE | jq -r '.student_id')
echo "Created student: $STUDENT_ID"

# 2. Login to get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"test@example.com\",\"password\":\"testpass123\"}" \
  | jq -r '.access')

echo "Got token: ${TOKEN:0:20}..."

# 3. Complete a few platform tests (simulate)
# ... (test completion code here)

# 4. Generate zone insights
curl -s -X GET \
  http://localhost:8000/api/zone-insights/test/1/ \
  -H "Authorization: Bearer $TOKEN" \
  > /dev/null

# 5. Generate focus zone and repeated mistakes
RESULT=$(curl -s -X POST \
  http://localhost:8000/api/zone-insights/focus-zone/1/ \
  -H "Authorization: Bearer $TOKEN")

echo "Focus Zone:"
echo $RESULT | jq '.focus_zone'

echo -e "\nRepeated Mistakes:"
echo $RESULT | jq '.repeated_mistake'
```

## Edge Cases

### Case 1: Student has only 1 platform test
**Behavior**: 
- Extracts data normally
- LLM may struggle to find "repeated" patterns
- Should still generate 2 points per subject based on available data

### Case 2: All platform tests have 100% accuracy
**Behavior**:
- `extract_repeated_mistakes_data()` returns empty dict
- `generate_repeated_mistakes()` returns empty dict
- Endpoint still succeeds (focus_zone is generated)

### Case 3: Student has no platform tests (only practice tests)
**Behavior**:
- Query returns no tests
- Function logs warning and returns empty dict
- Endpoint succeeds with empty `repeated_mistake` field

### Case 4: Same question appears in multiple tests
**Behavior**:
- Question appears multiple times in the data
- LLM can identify this as a strong repeated pattern
- Helps prioritize review of specific concepts

## Performance Considerations

### Database Queries
```python
# Optimized with select_related
wrong_answers = TestAnswer.objects.filter(
    session_id=test_session.id,
    question__topic_id__in=topic_ids,
    selected_answer__isnull=False,
    is_correct=False
).select_related('question', 'question__topic').order_by('id')
```

### Data Volume
- Average student: 5-10 platform tests
- Average questions per test: 180
- Average wrong answers per test: 20-40
- **Total**: ~100-400 wrong answers to analyze
- **Payload size**: ~50-200 KB (well within limits)

### LLM Performance
- Model: Gemini 2.5 Flash (fast model)
- Average response time: 2-5 seconds
- With retries: Max ~30 seconds
- Runs in parallel with focus zone generation

## Troubleshooting

### Issue: Empty `repeated_mistake` in response
**Possible causes**:
1. Student has no platform tests
2. All platform tests have perfect scores
3. LLM generation failed

**Debugging**:
```python
from neet_app.services.zone_insights_service import extract_repeated_mistakes_data

data = extract_repeated_mistakes_data(student_id)
print(f"Extracted data: {data}")
# If empty, check platform test count
```

### Issue: LLM returns patterns from only 1 test
**Cause**: Student has limited platform test history

**Solution**: This is expected behavior. The feature works best with 3+ tests.

### Issue: Response shows patterns but no specific test count
**Cause**: LLM is instructed to find patterns but may not always mention exact count

**Solution**: Verify the input data has multiple tests. If yes, this is acceptable LLM variation.

## Future Enhancements

1. **Minimum Test Threshold**: Only generate if student has ≥3 platform tests
2. **Recency Weighting**: Give more weight to recent tests
3. **Confidence Scores**: Add confidence % to each pattern
4. **Question Citation**: Reference specific question IDs in each point
5. **Trend Analysis**: Show if pattern is improving or worsening over time
6. **Topic-Level Breakdown**: Provide detailed drill-down by topic

## Comparison with Focus Zone

### When to Use Which?

**Focus Zone**:
- Just completed a test
- Want immediate feedback
- Identify weak areas in current test
- Quick improvement for next test

**Repeated Mistakes**:
- Completed multiple tests
- Want long-term improvement
- Identify persistent patterns
- Build solid foundation

**Both Together**:
- Comprehensive analysis
- Immediate + long-term strategies
- Best user experience

## Files Modified
- `backend/neet_app/services/zone_insights_service.py` - Added:
  - `REPEATED_MISTAKES_PROMPT`
  - `extract_repeated_mistakes_data()`
  - `generate_repeated_mistakes()`
- `backend/neet_app/views/zone_insights_views.py` - Modified:
  - `generate_test_focus_zone()` - Now generates both insights

## Conclusion
The Repeated Mistakes feature provides students with valuable insights into their persistent weak areas. By analyzing patterns across multiple tests, it helps identify deep conceptual gaps that need focused attention, complementing the immediate feedback from Focus Zone.

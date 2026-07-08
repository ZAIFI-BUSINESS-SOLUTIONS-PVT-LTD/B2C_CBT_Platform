# Focus Zone Implementation

## Overview
The Focus Zone feature generates AI-powered diagnostic insights for students based on their wrong and skipped questions in completed tests. It provides subject-wise focus points with clear "what went wrong" and "how to fix it" guidance.

## Architecture

### Database Schema
- **Field**: `focus_zone` in `TestSubjectZoneInsight` model
- **Type**: JSONField (list/dict)
- **Structure**:
```json
{
  "Physics": [
    "Student confused velocity with acceleration in motion equations.\nPractice 10 motion problems focusing on unit identification.",
    "Mistakenly applied scalar arithmetic to vector quantities.\nReview vector basics and solve 5 vector addition problems."
  ],
  "Chemistry": [
    "...",
    "..."
  ]
}
```

### Data Flow
1. **Test Completion** → Student completes a test
2. **Zone Insights Generation** → Call `/api/zone-insights/test/<test_id>/` to generate basic metrics
3. **Focus Zone Generation** → Call `/api/zone-insights/focus-zone/<test_id>/` to generate AI insights

## API Endpoints

### Generate Focus Zone
**Endpoint**: `POST /api/zone-insights/focus-zone/<test_id>/`

**Authentication**: Required (JWT Token)

**Request**: No body required

**Response**:
```json
{
  "status": "success",
  "test_id": 123,
  "focus_zone": {
    "Physics": [
      "Student confused velocity with acceleration in motion equations.\nPractice 10 motion problems focusing on unit identification.",
      "Mistakenly applied scalar arithmetic to vector quantities.\nReview vector basics and solve 5 vector addition problems."
    ],
    "Chemistry": [
      "Mixed up oxidation and reduction reactions in redox chemistry.\nMake a cheat sheet for common oxidation states and practice examples.",
      "Confused molecular vs empirical formulas in organic compounds.\nSolve 10 problems converting between molecular and empirical formulas."
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

### 1. Data Extraction (`extract_focus_zone_data`)
Extracts wrong and skipped questions from the test:
- **Wrong questions**: `selected_answer != None` AND `is_correct = False`
- **Skipped questions**: `selected_answer = None` AND `time_taken > 5 seconds`
  - Filters out questions with `time_taken = 0` (never viewed)

Groups questions by:
1. Subject (Physics, Chemistry, Botany, Zoology, Biology, Math)
2. Topic (within each subject)
3. Question metadata:
   - Question text
   - Options (A, B, C, D)
   - Correct answer
   - Selected answer (if any)
   - Misconception (if available from Question.misconceptions field)

### 2. LLM Prompt (`FOCUS_ZONE_PROMPT`)
The prompt instructs the LLM to:
- Analyze ALL wrong and skipped questions across subjects
- Identify the 2 most critical issues per subject
- Generate focus points with:
  - Line 1: What went wrong (10-15 words)
  - Line 2: How to fix it (10-15 words)
- Use simple, grade-appropriate language
- Be specific about concepts, not just topics

### 3. Focus Zone Generation (`generate_focus_zone`)
- Calls Gemini 2.5 Flash model via `GeminiClient`
- Implements retry logic (10 attempts with exponential backoff)
- Parses JSON response
- Validates structure (exactly 2 points per subject)
- Updates `TestSubjectZoneInsight.focus_zone` field
- Returns the generated focus zone data

### 4. Response Parsing (`parse_focus_zone_response`)
- Handles markdown code blocks
- Supports both JSON and Python dict formats (using `ast.literal_eval` as fallback)
- Validates structure and pads/truncates to exactly 2 points per subject
- Returns `None` if parsing fails (triggers retry)

## Usage Example

### Python (Backend Test)
```python
from neet_app.services.zone_insights_service import generate_focus_zone

# Generate focus zone for a completed test
test_id = 123
focus_zone_data = generate_focus_zone(test_id)

print(focus_zone_data)
# Output:
# {
#   "Physics": ["...", "..."],
#   "Chemistry": ["...", "..."],
#   ...
# }
```

### cURL
```bash
# First, generate zone insights
curl -X GET \
  http://localhost:8000/api/zone-insights/test/123/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Then, generate focus zone
curl -X POST \
  http://localhost:8000/api/zone-insights/focus-zone/123/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript (Frontend)
```javascript
const testId = 123;
const token = localStorage.getItem('access_token');

// Generate focus zone
const response = await fetch(`/api/zone-insights/focus-zone/${testId}/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data.focus_zone);
// Output:
// {
//   Physics: ["...", "..."],
//   Chemistry: ["...", "..."]
// }
```

## Key Features

### 1. Separate Endpoint
- Focus zone generation is **separate** from basic zone insights
- Allows frontend to call it on-demand (e.g., when user clicks "Get Focus Points")
- Avoids delaying test completion flow

### 2. Smart Question Filtering
- Only includes questions where student spent meaningful time (> 5s for skipped)
- Excludes questions never viewed (time_taken = 0)
- Focuses on genuine mistakes and struggles

### 3. AI-Powered Insights
- Uses Gemini 2.5 Flash for fast, accurate analysis
- Provides specific, actionable feedback
- Simple language appropriate for students

### 4. Robust Error Handling
- Retry logic for LLM failures
- Fallback parsing strategies (JSON → ast.literal_eval)
- Graceful degradation (returns empty dict on total failure)

### 5. Database Persistence
- Focus zone data saved in `TestSubjectZoneInsight.focus_zone`
- Can be retrieved later without regenerating
- Stored alongside other zone insight metrics

## Testing

### Manual Test Script
```python
# Run from backend/ directory
python scripts/run_zone_insights_now.py

# Then in Django shell:
from neet_app.services.zone_insights_service import generate_focus_zone
from neet_app.models import TestSession

# Get the most recent completed test
test = TestSession.objects.filter(is_completed=True).order_by('-end_time').first()
print(f"Testing with test_id: {test.id}")

# Generate focus zone
focus_zone = generate_focus_zone(test.id)
print(f"Focus zone generated: {focus_zone}")

# Verify it's saved
from neet_app.models import TestSubjectZoneInsight
insight = TestSubjectZoneInsight.objects.filter(test_session_id=test.id).first()
print(f"Saved focus_zone: {insight.focus_zone}")
```

### API Test
```bash
# 1. Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass"}' \
  | jq -r '.access')

# 2. Generate zone insights
curl -X GET \
  http://localhost:8000/api/zone-insights/test/1/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Generate focus zone
curl -X POST \
  http://localhost:8000/api/zone-insights/focus-zone/1/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.focus_zone'
```

## Environment Variables
Ensure these are set in your `.env` file:
```env
# Gemini API keys for LLM (at least one required)
GEMINI_API_KEY=your_gemini_api_key
# Or use multiple keys for rotation
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
# ... up to GEMINI_API_KEY_10
```

## Troubleshooting

### Issue: "Zone insights must be generated before focus zone"
**Solution**: Call `/api/zone-insights/test/<test_id>/` first to generate basic metrics.

### Issue: "Failed to generate focus zone. No data available"
**Possible causes**:
1. No wrong or skipped questions in the test (all correct)
2. All skipped questions have `time_taken <= 5s`
3. Test has no questions

**Solution**: Check test answers and ensure there are meaningful mistakes.

### Issue: LLM timeout or errors
**Possible causes**:
1. Gemini API key not set or invalid
2. Rate limit exceeded
3. Network issues

**Solution**: 
- Verify `GEMINI_API_KEY` in `.env`
- Use multiple API keys for rotation
- Check Gemini API quota and billing

### Issue: Parsing errors
**Symptoms**: Logs show "Could not parse focus zone response"

**Solution**: 
- Check LLM response format in logs
- Verify prompt is correctly formatted
- Retry logic should handle most cases automatically

## Future Enhancements
1. **Caching**: Cache focus zone for X hours to avoid redundant LLM calls
2. **Progressive Generation**: Generate focus zone in background (Celery task)
3. **Multilingual**: Support Hindi and other regional languages
4. **Personalization**: Include student's historical performance trends
5. **Question Citations**: Reference specific question IDs in focus points

## Files Modified
- `backend/neet_app/models.py` - `focus_zone` field already exists
- `backend/neet_app/services/zone_insights_service.py` - Added:
  - `FOCUS_ZONE_PROMPT`
  - `extract_focus_zone_data()`
  - `generate_focus_zone()`
  - `parse_focus_zone_response()`
- `backend/neet_app/views/zone_insights_views.py` - Added:
  - `generate_test_focus_zone()` endpoint
- `backend/neet_app/urls.py` - Added:
  - Route: `zone-insights/focus-zone/<int:test_id>/`

## Conclusion
The Focus Zone feature provides students with personalized, actionable insights based on their test performance. It leverages AI to identify specific misconceptions and provide targeted improvement strategies, making it a valuable tool for exam preparation.

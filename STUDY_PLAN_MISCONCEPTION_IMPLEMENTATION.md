# Study Plan Feature - Misconception-Based Implementation

## Summary

Successfully removed the old topic-classification-based study plan logic and replaced it with a new misconception-based approach that analyzes wrong answers from recent tests.

## Changes Made

### 1. New Service: `study_plan_service.py`
Created `backend/neet_app/services/study_plan_service.py` with:

**Key Functions:**
- `normalize_option_key()`: Maps option variants (A/a/option_a/1) to standard format
- `collect_wrong_answers_by_topic_and_test()`: Collects all wrong answers from last N tests, grouped by topic → test → questions
- `generate_study_plan_from_misconceptions()`: Main function that:
  - Collects wrong answers with their misconceptions
  - Groups by topic, then by test (chronologically)
  - Sends to LLM for analysis
  - Returns top 5 ranked study recommendations

**Data Structure:**
```json
{
  "topics": [
    {
      "topic_id": int,
      "topic_name": str,
      "subject": str,
      "total_wrong": int,
      "tests": [
        {
          "test_id": int,
          "test_name": str,
          "test_date": str,
          "questions": [
            {
              "question_id": int,
              "question_text": str,
              "selected_option": str,
              "selected_option_text": str,
              "misconception": str,
              "answered_at": str
            }
          ]
        }
      ]
    }
  ]
}
```

**LLM Prompt:**
- Analyzes repeated misconceptions across tests
- Identifies fundamental concept gaps
- Distinguishes careless mistakes from systematic misunderstandings
- Ranks recommendations by IMPACT and ACTIONABILITY
- Returns exactly 5 recommendations with:
  - Title, reasoning, concept gaps
  - 3-5 specific action steps
  - Topics to review, estimated time, priority
  - Affected questions count

### 2. New API Endpoint
**Route:** `GET /api/insights/study-plan/`
- **Authentication:** Required (student)
- **Query Parameters:** `max_tests` (1-10, default: 5)
- **Response:**
```json
{
  "status": "success|insufficient_data|error",
  "analysis_summary": "Brief overview",
  "recommendations": [...],  // Top 5 ranked
  "supporting_data": {
    "topics": [...],
    "total_wrong_questions": int,
    "tests_analyzed": int
  }
}
```

### 3. Removed Old Logic
**From `insights_views.py`:**
- ❌ Removed old study plan prompt template (lines ~217-238)
- ❌ Removed `study_plan_data` construction with weak/improvement/strength/unattempted topics
- ❌ Removed call to `generate_llm_insights('study_plan', study_plan_data)`

**Replaced with:**
- ✅ Direct call to `generate_study_plan_from_misconceptions()` in `get_student_insights()`
- ✅ Formats result to match expected `llm_insights['study_plan']` structure
- ✅ Maintains backward compatibility with response structure

### 4. Updated URL Routing
**File:** `backend/neet_app/urls.py`
- Added import: `get_study_plan`
- Added route: `path('insights/study-plan/', get_study_plan, name='study-plan')`

### 5. Backward Compatibility
- ✅ `get_student_insights()` still returns `llm_insights['study_plan']` in same format
- ✅ `get_insights_config()` updated to note dynamic classification
- ✅ All existing endpoints unchanged
- ✅ Database schema unchanged (reuses existing `StudentInsight.llm_study_plan` field)

## Key Features

### No Pre-Aggregation
- LLM receives raw grouped data (topic → test → questions)
- All wrong questions included (no artificial caps)
- LLM performs its own pattern analysis and ranking

### Comprehensive Data
For each wrong question sent to LLM:
- Full question text
- Topic name and subject
- Selected option and text
- Misconception for that specific option
- Test name and date
- Chronological ordering

### Smart Ranking
LLM ranks recommendations by:
1. **Impact**: How much improvement it would create
2. **Actionability**: How clear and concrete the steps are

### Handles Edge Cases
- Missing misconceptions: Falls back to "Misconception not available"
- No wrong answers: Returns insufficient_data status
- LLM errors: Returns error status with message
- Very large payloads: Could add truncation later (noted in TODO)

## Testing

**Test Script:** `backend/test_study_plan.py`
- Tests data collection and grouping
- Tests LLM integration
- Validates response structure
- Can be run with: `python backend/test_study_plan.py`

## Usage Examples

### For Students (via new endpoint)
```bash
GET /api/insights/study-plan/?max_tests=5
Authorization: Bearer <token>
```

### Automatic (via existing insights)
```bash
GET /api/insights/student/
Authorization: Bearer <token>
```
The response includes `llm_insights.study_plan` with recommendations from the new system.

## Next Steps (TODO)

1. ✅ Collector and grouping - DONE
2. ✅ LLM integration - DONE
3. ✅ API endpoint - DONE
4. ✅ Remove old logic - DONE
5. ⏳ Add comprehensive tests
6. ⏳ Add payload size safeguards (truncation/pagination for very large datasets)
7. ⏳ Add performance monitoring and caching
8. ⏳ Frontend integration

## Migration Notes

- No database migrations required
- No breaking changes to existing APIs
- Old study plan logic completely removed
- New logic automatically active for all students
- Works with existing misconception generation system

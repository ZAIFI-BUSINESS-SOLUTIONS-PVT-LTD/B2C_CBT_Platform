# Question Exclusion Logic Implementation

## Overview
This implementation adds question exclusion logic to prevent students from getting the same questions in consecutive tests. Students will not see questions that appeared in their last 3 completed test sessions.

## Key Features

### 1. Configurable Exclusion Count
- The number of recent tests to check is configurable via Django settings
- Default: 3 tests
- Setting: `NEET_SETTINGS['RECENT_TESTS_COUNT_FOR_EXCLUSION']`

### 2. Intelligent Fallback Logic
The system handles edge cases gracefully:

1. **Sufficient Non-Recent Questions**: Uses only fresh questions
2. **Insufficient Pool**: Uses all available fresh questions, then fills gaps with recent questions if necessary
3. **No Questions for Selected Topics**: Falls back to questions from any available topics
4. **Complete Pool Exhaustion**: Uses all available questions (ignoring exclusions)

### 3. Performance Optimized
- Uses database indexes on `student_id` and `start_time` fields
- Efficient querying with `distinct()` and `values_list()`
- Minimal memory footprint with set operations

## Implementation Details

### Files Modified

1. **`neet_backend/settings.py`**
   - Added `NEET_SETTINGS` configuration
   - Configurable recent tests count

2. **`neet_app/models.py`**
   - Added `TestSession.get_recent_question_ids_for_student()` static method
   - Fetches question IDs from recent completed test sessions

3. **`neet_app/views/utils.py`**
   - Enhanced `generate_questions_for_topics()` function
   - Added `exclude_question_ids` parameter
   - Implemented intelligent fallback logic

4. **`neet_app/serializers.py`**
   - Updated `TestSessionCreateSerializer.create()` method
   - Calculates recent question IDs during session creation

5. **`neet_app/views/test_session_views.py`**
   - Updated question generation to use exclusion logic
   - Maintains backward compatibility

### API Changes

The existing API endpoints remain unchanged. The exclusion logic is automatically applied behind the scenes:

- `POST /api/test-sessions/` - Creates test session with question exclusion
- All existing parameters work as before
- No frontend changes required

### Database Impact

- Uses existing `TestAnswer` records to track question usage
- No new tables or migrations required
- Leverages existing indexes for performance

## Usage Examples

### Test Session Creation (No Changes Required)
```python
# Frontend request remains the same
POST /api/test-sessions/
{
    "selected_topics": ["1", "2", "3"],
    "question_count": 10,
    "time_limit": 60
}
```

### Manual Question Generation with Exclusion
```python
from neet_app.models import TestSession
from neet_app.views.utils import generate_questions_for_topics

# Get recent question IDs for a student
recent_ids = TestSession.get_recent_question_ids_for_student("STU241001ABC123")

# Generate questions excluding recent ones
questions = generate_questions_for_topics(
    selected_topics=["1", "2", "3"],
    question_count=10,
    exclude_question_ids=recent_ids
)
```

## Configuration

### Settings Configuration
```python
# In settings.py
NEET_SETTINGS = {
    'RECENT_TESTS_COUNT_FOR_EXCLUSION': 3,  # Number of recent tests to check
}
```

### Runtime Configuration
The exclusion count can be modified without code changes by updating the settings file.

## Testing

A test script is provided to verify the exclusion logic:

```bash
cd backend
python test_question_exclusion.py
```

The test:
1. Creates a test student
2. Creates 3 completed test sessions with questions
3. Generates a new test and verifies no question overlap
4. Cleans up test data

## Monitoring and Logging

The system provides detailed logging for monitoring:

- Question pool sizes before and after exclusion
- Fallback strategy usage
- Number of excluded questions in final selection

Log messages help diagnose issues and monitor system behavior.

## Performance Considerations

### Database Queries
- Recent question lookup: 1 query per student
- Question generation: 1-3 queries depending on fallback usage
- Bulk operations for TestAnswer creation

### Memory Usage
- Question IDs stored as sets for efficient lookup
- Minimal memory overhead for exclusion logic

### Scalability
- Efficient for up to ~1000 questions per topic
- Performance scales linearly with question pool size
- Database indexes ensure fast recent session lookups

## Backward Compatibility

- All existing API endpoints work unchanged
- Existing test creation logic preserved
- No frontend modifications required
- Can be disabled by setting `RECENT_TESTS_COUNT_FOR_EXCLUSION` to 0

## Error Handling

The system handles various edge cases:

1. **New Students**: No recent tests to exclude
2. **Insufficient Questions**: Falls back gracefully
3. **Database Errors**: Logs errors and continues with available questions
4. **Configuration Errors**: Uses default values

## Future Enhancements

Possible future improvements:
1. Subject-wise exclusion rules
2. Difficulty-based exclusion
3. Time-based exclusion (e.g., questions from last 30 days)
4. Admin interface for exclusion rule management

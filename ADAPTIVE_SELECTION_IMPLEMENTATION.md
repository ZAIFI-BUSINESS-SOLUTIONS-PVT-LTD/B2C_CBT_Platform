# Adaptive Question Selection Implementation

## Overview
This implementation adds adaptive question selection logic that improves student learning by strategically selecting questions based on their performance history. The system automatically allocates questions across three buckets with intelligent fallback mechanisms.

## Key Features

### 1. Three-Bucket Strategy
- **Bucket A (New)**: 60% - Questions never attempted by the student
- **Bucket B (Wrong/Unanswered)**: 30% - Questions answered incorrectly or left unanswered
- **Bucket C (Correct)**: 10% - Questions answered correctly

### 2. Intelligent Fallback Logic
The system handles edge cases gracefully with priority-based fallback:

**Bucket A (New) shortage** → fill from Bucket B first, then Bucket C
**Bucket B (Wrong/Unanswered) shortage** → fill from Bucket A first, then Bucket C  
**Bucket C (Correct) shortage** → fill from Bucket B first, then Bucket A

### 3. Configurable Ratios
All ratios are configurable via Django settings:
```python
NEET_SETTINGS = {
    'ADAPTIVE_SELECTION_ENABLED': False,  # Feature flag
    'ADAPTIVE_RATIO_NEW': 60,            # Percentage for new questions
    'ADAPTIVE_RATIO_WRONG': 30,          # Percentage for wrong/unanswered
    'ADAPTIVE_RATIO_CORRECT': 10,        # Percentage for correct questions
}
```

## Implementation Details

### Files Modified

1. **`neet_backend/settings.py`**
   - Added adaptive selection configuration
   - Feature flag for enabling/disabling

2. **`neet_app/views/utils.py`**
   - Added `adaptive_generate_questions_for_topics()` function
   - Added `adaptive_generate_random_questions_from_database()` function
   - Implements bucket logic with fallback mechanisms

3. **`neet_app/serializers.py`**
   - Added `adaptive_selection` boolean field to `TestSessionCreateSerializer`
   - Backward compatible with existing API

4. **`neet_app/views/test_session_views.py`**
   - Updated to use adaptive selection when flag is enabled
   - Maintains compatibility with existing selection logic

5. **`test_adaptive_selection.py`**
   - Comprehensive test script for validation

### API Changes

The existing API endpoints remain unchanged. Adaptive selection is opt-in via a new parameter:

```json
POST /api/test-sessions/
{
    "selected_topics": ["1", "2", "3"],
    "question_count": 20,
    "time_limit": 60,
    "adaptive_selection": true
}
```

### Database Impact

- Uses existing `TestAnswer` records to analyze student performance
- No new tables or migrations required
- Leverages existing indexes for performance

## Usage Examples

### 1. Topic-Based Test with Adaptive Selection
```python
# Frontend request
POST /api/test-sessions/
{
    "selected_topics": ["1", "2", "3"],
    "question_count": 20,
    "time_limit": 60,
    "adaptive_selection": true,
    "test_type": "search"
}
```

### 2. Random Test with Adaptive Selection
```python
# Frontend request
POST /api/test-sessions/
{
    "selected_topics": [],
    "question_count": 20,
    "time_limit": 60,
    "adaptive_selection": true,
    "test_type": "random"
}
```

### 3. Manual Question Generation
```python
from neet_app.views.utils import adaptive_generate_questions_for_topics

questions = adaptive_generate_questions_for_topics(
    selected_topics=["1", "2", "3"],
    question_count=20,
    student_id="STU241001ABC123",
    exclude_question_ids=set()
)
```

## Algorithm Details

### Step 1: Bucket Classification
1. Query student's answer history for available questions
2. Classify questions into three buckets:
   - **New**: Never attempted
   - **Wrong/Unanswered**: `is_correct = False` or `selected_answer = None`
   - **Correct**: `is_correct = True`

### Step 2: Target Allocation
1. Calculate target counts based on ratios:
   - New: `question_count * 0.60`
   - Wrong: `question_count * 0.30`
   - Correct: `question_count * 0.10`
2. Adjust for rounding errors (add remainder to New bucket)

### Step 3: Primary Selection
1. Select questions from each bucket up to target count
2. Use random selection within each bucket (`order_by('?')`)

### Step 4: Fallback Allocation
If any bucket cannot meet its target:
1. Calculate shortage for each bucket
2. Apply priority-based fallback rules
3. Fill shortages from other buckets in priority order

### Step 5: Final Guarantee
1. If still short of total count, select from any remaining questions
2. Always deliver the requested number of questions

## Example Scenarios

### Case 1: Plenty of All Buckets
- Target: 20 questions → 12 new, 6 wrong, 2 correct
- Available: 50 new, 30 wrong, 20 correct
- Result: Perfect 60/30/10 distribution

### Case 2: Low New Questions
- Available: 5 new, 30 wrong, 20 correct
- Selection: 5 new + 7 from wrong (filling new quota) + 6 wrong + 2 correct
- Result: Adapts to available questions while prioritizing learning

### Case 3: Experienced Student (Few New Questions)
- Available: 2 new, 25 wrong, 40 correct
- Selection: 2 new + 10 from wrong (for new shortage) + 6 wrong + 2 correct
- Result: Focuses on reinforcement and review

## Performance Considerations

### Database Queries
- Student answer history: 1 query with joins
- Question selection: 3-6 queries (one per bucket + fallbacks)
- Bulk TestAnswer creation: 1 query

### Memory Usage
- Question IDs stored as sets for efficient operations
- Minimal memory overhead for bucket management

### Scalability
- Efficient for up to ~10,000 questions per topic
- Performance scales linearly with question pool size
- Database indexes ensure fast history lookups

## Testing

Run the comprehensive test script:
```bash
cd backend
python test_adaptive_selection.py
```

The test:
1. Creates a test student with varied performance history
2. Tests topic-based adaptive selection
3. Tests random adaptive selection
4. Analyzes bucket distribution
5. Validates fallback mechanisms
6. Cleans up test data

## Monitoring and Logging

The system provides detailed logging for monitoring:
- Bucket sizes and target allocations
- Fallback strategy usage
- Final question distribution
- Performance metrics

Log messages help diagnose issues and monitor system behavior.

## Backward Compatibility

- All existing API endpoints work unchanged
- Default behavior remains the same (adaptive_selection=false)
- Existing test creation logic preserved
- No frontend modifications required for basic functionality
- Can be disabled via feature flag

## Error Handling

The system handles various edge cases:
1. **New Students**: No history → mostly new questions
2. **No Questions Available**: Graceful failure with appropriate error
3. **Insufficient Questions**: Adaptive allocation with logging
4. **Database Errors**: Fallback to traditional selection
5. **Configuration Errors**: Uses default ratios

## Configuration

### Settings Configuration
```python
# In settings.py
NEET_SETTINGS = {
    'ADAPTIVE_SELECTION_ENABLED': True,   # Enable feature
    'ADAPTIVE_RATIO_NEW': 60,            # 60% new questions
    'ADAPTIVE_RATIO_WRONG': 30,          # 30% wrong/unanswered
    'ADAPTIVE_RATIO_CORRECT': 10,        # 10% correct questions
}
```

### Runtime Configuration
Ratios can be modified without code changes by updating the settings file.

## Future Enhancements

Possible future improvements:
1. **Subject-wise Adaptive Ratios**: Different ratios per subject
2. **Difficulty-based Selection**: Consider question difficulty in allocation
3. **Time-based Decay**: Weight recent performance more heavily
4. **Machine Learning Integration**: Dynamic ratio adjustment based on learning patterns
5. **Admin Dashboard**: Visual interface for monitoring and configuration
6. **A/B Testing Framework**: Compare traditional vs adaptive selection effectiveness

## Migration Guide

### For Existing Installations
1. Update `settings.py` with adaptive configuration
2. Deploy new code (backward compatible)
3. Optionally enable adaptive selection via feature flag
4. Test with selected users before full rollout

### For New Installations
1. Adaptive selection is available but disabled by default
2. Enable via settings when ready to use
3. No additional setup required

## Benefits

### For Students
- **Improved Learning**: Focus on areas needing attention
- **Reduced Repetition**: Fewer questions they already know
- **Better Retention**: Strategic reinforcement of weak areas
- **Adaptive Difficulty**: Natural progression as skills improve

### For Educators
- **Data-driven Selection**: Based on actual performance
- **Configurable Parameters**: Adjust ratios based on pedagogy
- **Monitoring Capabilities**: Track selection effectiveness
- **Backward Compatibility**: Can revert if needed

### For Platform
- **Competitive Advantage**: Advanced question selection algorithm
- **Improved Engagement**: Students see more relevant questions
- **Better Outcomes**: Enhanced learning effectiveness
- **Scalable Solution**: Handles growing user base efficiently

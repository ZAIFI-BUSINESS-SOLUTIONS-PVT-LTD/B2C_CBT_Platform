# Rerun Test Results and Insights

## Overview

This script regenerates test results, zone insights, and student insights for a specific test. It's useful when:
- Questions' correct answers have been updated
- Session aggregates need recalculation
- Zone insights need to be regenerated
- Student insights need to be refreshed

## What It Does

The script performs three main operations:

1. **Recalculates Session Aggregates**
   - Updates `correct_answers`, `incorrect_answers`, `unanswered` counts
   - Recalculates subject-wise scores (Physics, Chemistry, Botany, Zoology, Math)
   - Updates `TestSession` records in the database

2. **Regenerates Zone Insights**
   - Deletes old zone insights for affected sessions
   - Generates fresh zone insights using `generate_all_subject_zones()`
   - Creates new `TestSubjectZoneInsight` records with:
     - Steady Zone (2 points)
     - Edge Zone (2 points)
     - Focus Zone (2 points)

3. **Regenerates Student Insights**
   - Recalculates topic metrics for each affected student
   - Classifies topics into strengths, weaknesses, improvements
   - Optionally generates LLM-based insights
   - Updates `StudentInsight` records

## Usage

### Quick Start

```powershell
# From backend directory
cd backend

# List all available tests
python scripts/rerun_test_insights.py --list-tests

# Rerun insights for a specific test
python scripts/rerun_test_insights.py --test-name "NEET 2024 Sample Test"

# Skip LLM generation for faster processing
python scripts/rerun_test_insights.py --test-name "NEET 2024 Sample Test" --skip-llm
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--test-name TEXT` | Name of the test to process (required unless `--list-tests`) |
| `--skip-llm` | Skip LLM-based insight generation (faster, uses fallbacks) |
| `--list-tests` | List all available tests and exit |
| `--help` | Show help message |

### Examples

**Example 1: List all tests**
```powershell
python scripts/rerun_test_insights.py --list-tests
```

Output:
```
================================================================================
📋 AVAILABLE PLATFORM TESTS
================================================================================

  Test Name: NEET 2024 Official Paper
  Test Code: NEET_2024_OFFICIAL [Official]
  Status: ✅ Active
  Sessions: 45 completed
  Created: 2024-11-01 10:30

  Test Name: JEE Mains Mock 1
  Test Code: JEE_MOCK_1 [Mock]
  Status: ✅ Active
  Sessions: 23 completed
  Created: 2024-11-05 14:15
```

**Example 2: Rerun insights with LLM**
```powershell
python scripts/rerun_test_insights.py --test-name "NEET 2024 Official Paper"
```

**Example 3: Fast mode (skip LLM)**
```powershell
python scripts/rerun_test_insights.py --test-name "NEET 2024 Official Paper" --skip-llm
```

## Alternative: Using Django Shell

You can also run the base script directly from Django shell:

```powershell
cd backend
python manage.py shell
```

Then in the shell:
```python
# Edit the TEST_NAME variable in the script first
exec(open('scripts/rerun_results_and_insights.py').read())
```

## What Gets Updated

### Database Tables Modified

1. **test_sessions**
   - `correct_answers`
   - `incorrect_answers`
   - `unanswered`
   - `total_questions`
   - `physics_score`, `chemistry_score`, `botany_score`, `zoology_score`, `math_score`

2. **test_subject_zone_insights**
   - Deletes old records for affected sessions
   - Creates new records with fresh zone insights
   - Fields: `steady_zone`, `edge_zone`, `focus_zone`

3. **student_insights** (via `save_insights_to_database`)
   - Updates cached insights for affected students
   - Includes topic classifications, LLM insights, and summaries

## Performance Considerations

- **Session aggregates**: Fast (direct DB queries)
- **Zone insights**: Moderate (LLM API calls per session/subject)
- **Student insights**: Slow if LLM enabled (multiple API calls per student)

**Recommendations:**
- Use `--skip-llm` for faster processing during development/testing
- Run during off-peak hours for production
- For very large tests (100+ sessions), consider batching or async processing

## Verification Steps

After running the script:

1. **Check Django Admin**
   - Verify session aggregates look correct
   - Check zone insights are present

2. **Test API Endpoints**
   ```bash
   # Zone insights
   curl http://localhost:8001/api/zone-insights/test/<test_id>/
   
   # Student insights
   curl http://localhost:8001/api/insights/student/<student_id>/
   ```

3. **Review Frontend**
   - Check student dashboard shows updated insights
   - Verify zone insights card displays correctly
   - Confirm test results match expected values

## Troubleshooting

### Error: "No PlatformTest found with test_name='...'"

**Solution:** Use `--list-tests` to see exact test names. Names are case-sensitive and must match exactly.

### Error: "No completed sessions found"

**Solution:** Verify that:
- The test has been taken by at least one student
- Sessions have `is_completed=True`
- Sessions are linked to the correct `platform_test_id`

### LLM Insights Fail

**Solution:** 
- Check GEMINI_API_KEY is set in environment
- Use `--skip-llm` to bypass LLM generation
- Check logs for specific API errors

### Zone Insights Not Generated

**Solution:**
- Ensure test has questions with valid `topic_id`
- Check that `physics_topics`, `chemistry_topics`, etc. are populated in sessions
- Review `zone_insights_service.py` logs

## Files Modified

1. **scripts/rerun_results_and_insights.py**
   - Base script (can be run via Django shell)
   - Set `TEST_NAME` variable at the top

2. **scripts/rerun_test_insights.py** (NEW)
   - CLI wrapper with argument parsing
   - Recommended for production use

## Related Code

- `neet_app/models.py`: `TestSession.calculate_and_update_subject_scores()`
- `neet_app/services/zone_insights_service.py`: `generate_all_subject_zones()`
- `neet_app/views/insights_views.py`: Insight generation functions
- `neet_app/tasks.py`: `generate_zone_insights_task()` (async version)

## Need Help?

Contact the development team or check:
- `TESTING_GUIDE.md` for test setup
- `IMPLEMENTATION_SUMMARY.md` for system architecture
- Django admin logs for detailed error messages

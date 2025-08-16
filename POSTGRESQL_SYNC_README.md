# PostgreSQL Sync Functions Documentation

## Overview
This document describes the new PostgreSQL-based sync functions that replace the Neo4j-based sync functionality. These functions sync data from the `database_question` table to the `Topic` and `Question` models with built-in duplicate prevention.

## New Functions

### 1. `sync_topics_from_database_question`
**Endpoint:** `GET /dashboard/sync-topics/`

**Purpose:** Syncs unique topics from the `database_question` table to the `Topic` model.

**Features:**
- Extracts unique combinations of (subject, chapter, topic) from `database_question`
- Only creates new topics that don't already exist
- Skips topics with empty names
- Uses transaction for atomicity

**Response Example:**
```json
{
    "status": "success",
    "message": "PostgreSQL topic sync completed.",
    "topics_synced": 45,
    "topics_skipped_duplicates": 12,
    "topics_failed_to_save": 0,
    "total_unique_topics_found": 57,
    "errors": []
}
```

### 2. `sync_questions_from_database_question`
**Endpoint:** `GET /dashboard/sync-questions/`

**Purpose:** Syncs questions from the `database_question` table to the `Question` model.

**Features:**
- Links questions to existing topics (requires topics to be synced first)
- Validates question data (text, options, correct answer)
- Cleans mathematical expressions using `clean_mathematical_text`
- Prevents duplicate questions based on content and topic
- Handles various correct answer formats (A/B/C/D, 1/2/3/4, etc.)

**Response Example:**
```json
{
    "status": "success",
    "message": "Successfully created 1250 questions from database_question table",
    "questions_created": 1250,
    "questions_skipped": 45,
    "total_processed": 1295,
    "errors_count": 3,
    "missing_topics": ["Advanced Quantum Physics"],
    "missing_topics_count": 1
}
```

### 3. `sync_all_from_database_question`
**Endpoint:** `GET /dashboard/sync-all/`

**Purpose:** Performs complete sync - first topics, then questions.

**Features:**
- Combines both sync operations
- Provides summary statistics
- Returns detailed results from both operations

### 4. `reset_questions_and_topics`
**Endpoint:** `DELETE /dashboard/reset-data/`

**Purpose:** Clears all existing Topic and Question data for fresh sync.

**Warning:** This will delete ALL existing topics and questions!

### 5. `clean_existing_questions`
**Endpoint:** `GET /dashboard/clean-existing-questions/`

**Purpose:** Cleans mathematical expressions in existing questions.

## Database Schema Changes

### Topic Model Constraints
```python
class Meta:
    unique_together = [['name', 'subject', 'chapter']]
```

### Question Model Constraints
```python
class Meta:
    unique_together = [['question', 'topic', 'option_a', 'option_b', 'option_c', 'option_d']]
```

## Usage Workflow

### Initial Setup (Fresh Database)
1. `GET /dashboard/sync-all/` - Sync everything at once
   
   OR
   
1. `GET /dashboard/sync-topics/` - Sync topics first
2. `GET /dashboard/sync-questions/` - Sync questions

### Adding New Data (Incremental Updates)
When new data is added to `database_question` table:

1. `GET /dashboard/sync-topics/` - Add any new topics
2. `GET /dashboard/sync-questions/` - Add new questions

The functions will automatically skip existing topics/questions, only adding new ones.

### Reset and Refresh (Complete Refresh)
If you need to completely refresh the data:

1. `DELETE /dashboard/reset-data/` - Clear existing data
2. `GET /dashboard/sync-all/` - Sync everything fresh

## Database Migration

After updating the models, run:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Duplicate Prevention Logic

### Topics
Duplicates are prevented by checking for existing topics with the same:
- `name`
- `subject` 
- `chapter`

### Questions
Duplicates are prevented by checking for existing questions with the same:
- `question` (text content)
- `topic` (foreign key)
- `option_a`, `option_b`, `option_c`, `option_d` (all options)

## Error Handling

- All functions use database transactions for atomicity
- Detailed error logging for debugging
- Graceful handling of missing topics
- Validation of required fields
- Mathematical text cleaning with fallback to original on errors

## Performance Considerations

- Functions process data in batches where applicable
- Database transactions ensure consistency
- Filtering applied at database level to reduce memory usage
- Unique constraints prevent duplicate processing

## Monitoring

Each function returns detailed statistics:
- Items processed/created/skipped
- Error counts and details
- Missing dependencies
- Processing recommendations

## Migration from Neo4j

The old Neo4j functions have been replaced:
- `sync_neo4j_to_postgresql` → `sync_topics_from_database_question`
- `sync_questions_from_neo4j` → `sync_questions_from_database_question`
- `reset_chapter_structure` → `reset_questions_and_topics`

## Best Practices

1. **Always sync topics before questions** - Questions need existing topics to link to
2. **Monitor error responses** - Check for missing topics or validation issues
3. **Use incremental sync** - For regular updates, just run sync functions again
4. **Backup before reset** - The reset function permanently deletes data
5. **Check mathematical cleaning** - Verify complex mathematical expressions are cleaned properly

# Institution Test Upload - Excel Format Specification

## Overview
This document specifies the Excel format required for institution admins to upload questions and automatically create tests.

## Database Schema Analysis

### Topic Model Fields (Required for Question Association)
- `name` (text, required) - Topic name
- `subject` (text, required) - Subject classification (Physics, Chemistry, Botany, Zoology)
- `icon` (text, required) - Icon representation (auto-set to 📚)
- `chapter` (text, optional) - Chapter information

### Question Model Fields
**Required Fields:**
- `question` (text) - The question text
- `option_a` (text) - Option A
- `option_b` (text) - Option B
- `option_c` (text) - Option C
- `option_d` (text) - Option D
- `correct_answer` (char, 1 letter) - A, B, C, or D
- `explanation` (text) - Explanation for the correct answer
- `topic` (ForeignKey) - Link to Topic (created/found based on topic_name + subject)

**Optional Fields:**
- `difficulty` (text) - Easy, Moderate, or Hard
- `question_type` (text) - Type of question
- `institution` (auto-set by upload)
- `institution_test_name` (auto-set by upload)
- `exam_type` (auto-set by upload)

## Excel Format Requirements

### Required Columns

| Column Name | Description | Data Type | Example | Validation Rules |
|-------------|-------------|-----------|---------|------------------|
| `question_text` | The question stem/text | Text | "What is the SI unit of force?" | Cannot be empty |
| `option_a` | First option | Text | "Newton" | Cannot be empty |
| `option_b` | Second option | Text | "Joule" | Cannot be empty |
| `option_c` | Third option | Text | "Watt" | Cannot be empty |
| `option_d` | Fourth option | Text | "Pascal" | Cannot be empty |
| `correct_answer` | The correct option | Text | "A" or "B" or "C" or "D" | Must be A/B/C/D (case-insensitive) |
| `explanation` | Explanation for answer | Text | "Newton is the SI unit of force..." | Cannot be empty |

### IMPORTANT: New Required Columns for Proper Data Storage

| Column Name | Description | Data Type | Example | Validation Rules |
|-------------|-------------|-----------|---------|------------------|
| **`topic_name`** | Topic/concept name | Text | "Newton's Laws of Motion" | **REQUIRED** - Used to create/link Topic |
| **`subject`** | Subject classification | Text | "Physics" | **REQUIRED** - Must be: Physics, Chemistry, Botany, or Zoology |

**WHY THESE ARE REQUIRED:**
- The `Topic` model requires both `name` and `subject` fields (non-nullable in database)
- Questions MUST be linked to a Topic via ForeignKey
- Subject is essential for:
  - Test session classification (physics_topics, chemistry_topics, etc.)
  - Subject-wise scoring (physics_score, chemistry_score, etc.)
  - Analytics and performance tracking

### Optional Columns

| Column Name | Description | Data Type | Example | Allowed Values |
|-------------|-------------|-----------|---------|----------------|
| `difficulty` | Question difficulty | Text | "Moderate" | Easy, Moderate, Hard (case-insensitive) |
| `question_type` | Type of question | Text | "Conceptual" | Any text value |
| `chapter` | Chapter information | Text | "Chapter 5" | Any text value |

### Accepted Column Name Variations (Case-Insensitive)

The parser recognizes multiple column name formats:

**question_text:** `question_text`, `question`, `q`, `question_stem`
**option_a:** `option_a`, `a`, `option1`
**option_b:** `option_b`, `b`, `option2`
**option_c:** `option_c`, `c`, `option3`
**option_d:** `option_d`, `d`, `option4`
**correct_answer:** `correct_answer`, `answer`, `correct`, `correct_option`
**explanation:** `explanation`, `explain`, `solution`
**topic_name:** `topic_name`, `topic`, `subject_topic`
**subject:** `subject`, `subject_name`
**difficulty:** `difficulty`, `level`, `difficulty_level`
**question_type:** `question_type`, `type`, `q_type`

### Correct Answer Format

The parser accepts multiple formats for correct answers:
- Single letter: `A`, `B`, `C`, `D` (case-insensitive)
- Full text: `OPTION_A`, `OPTION A`, `Option A`
- Numbers: `1`, `2`, `3`, `4` (1=A, 2=B, 3=C, 4=D)
- Words: `FIRST`, `SECOND`, `THIRD`, `FOURTH`

All formats are normalized to single uppercase letters (A/B/C/D) in the database.

## Excel File Constraints

- **Maximum file size:** 10 MB
- **Maximum rows:** 5,000 questions per upload
- **Sheet:** First sheet in the workbook is used
- **Header row:** Must be the first row (Row 1)
- **Data rows:** Start from Row 2 onwards
- **Empty rows:** Automatically skipped

## Sample Excel Format

### Recommended Format (With All Fields)

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject | difficulty | question_type | chapter |
|---------------|----------|----------|----------|----------|----------------|-------------|------------|---------|------------|---------------|---------|
| What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton (N) is the SI unit of force, defined as kg⋅m/s². | Newton's Laws | Physics | Easy | Conceptual | Chapter 5 |
| Which organ performs photosynthesis? | Root | Stem | Leaf | Flower | C | Leaves contain chlorophyll and perform photosynthesis to produce food. | Photosynthesis | Botany | Easy | Knowledge | Chapter 2 |

### Minimum Required Format

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject |
|---------------|----------|----------|----------|----------|----------------|-------------|------------|---------|
| What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton (N) is the SI unit... | Newton's Laws | Physics |
| Which organ performs photosynthesis? | Root | Stem | Leaf | Flower | C | Leaves contain chlorophyll... | Photosynthesis | Botany |

## Upload Process Flow

### Parser Logic Review

1. **File Validation**
   - Check file size (max 10MB)
   - Verify Excel format can be opened

2. **Header Parsing**
   - Read first row to identify column positions
   - Map user column names to standard names using variants
   - Validate all required columns are present
   - If missing: raise error with list of missing columns

3. **Row Parsing (Row 2 onwards)**
   - Skip completely empty rows
   - Extract all field values based on column positions
   - Validate required fields are not empty
   - Normalize correct_answer to A/B/C/D format
   - Handle optional fields (default to None if not present)

4. **Topic Creation/Retrieval**
   - **CURRENT LOGIC (PROBLEMATIC):**
     ```python
     if not topic_name:
         # Creates default topic
         topic_name = f"{institution.name} - {exam_type.upper()} Questions"
         subject = exam_type.upper()  # Uses exam_type as subject
     else:
         # Uses keyword inference for subject
         # Checks if keywords like 'physics', 'chemistry' are in topic_name
     ```
   
   - **ISSUE:** Subject inference from topic_name keywords is unreliable
   - **SOLUTION:** Require explicit `subject` column in Excel

5. **Question Creation**
   - Create Question record for each row
   - Link to topic via topic ForeignKey
   - Set institution-specific fields:
     - `institution` = current institution
     - `institution_test_name` = provided test name
     - `exam_type` = selected exam type

6. **Test Creation**
   - Generate unique test_code
   - Create PlatformTest with:
     - `is_institution_test` = True
     - `selected_topics` = list of unique topic IDs from questions
     - `total_questions` = count of questions created
     - `time_limit` = provided or default (180 minutes)

### Transaction Safety
- Entire upload is wrapped in `@transaction.atomic`
- If any error occurs, all changes are rolled back
- Database remains consistent even on failure

## Parser Logic Issues & Fixes Needed

### ❌ Issue 1: Subject Field Not Parsed from Excel
**Current State:**
```python
# Parser tries to infer subject from topic_name keywords
if any(keyword in topic_name.lower() for keyword in ['physics', 'mechanics']):
    subject = 'Physics'
# ... more keyword checks
```

**Problem:**
- Unreliable keyword matching
- Subject is non-nullable in Topic model
- No explicit subject column parsed from Excel

**Fix Required:**
```python
# Add to REQUIRED_COLUMNS
REQUIRED_COLUMNS = {
    # ... existing columns
    'subject': ['subject', 'subject_name'],  # ADD THIS
}

# In parse_excel_rows function
subject = row[headers['subject']]  # Extract from Excel
if not subject or str(subject).strip() == '':
    raise UploadValidationError(f"Row {row_idx}: Subject is empty")

# Validate subject value
valid_subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology']
subject = subject.strip().capitalize()
if subject not in valid_subjects:
    raise UploadValidationError(
        f"Row {row_idx}: Invalid subject '{subject}'. "
        f"Must be one of: {', '.join(valid_subjects)}"
    )

# Pass to get_or_create_topic
topic = get_or_create_topic(topic_name, subject, exam_type, institution)
```

### ❌ Issue 2: topic_name is Optional but Required for Proper Data
**Current State:**
```python
topic_name = None
if 'topic_name' in headers:
    topic_name = row[headers['topic_name']]

if not topic_name:
    # Creates generic topic like "Vetri Coaching - NEET Questions"
    topic_name = f"{institution.name} - {exam_type.upper()} Questions"
```

**Problem:**
- All questions get same generic topic name
- Loses granularity for analytics
- Can't track topic-wise performance

**Fix Required:**
```python
# Move topic_name to REQUIRED_COLUMNS
REQUIRED_COLUMNS = {
    # ... existing
    'topic_name': ['topic_name', 'topic', 'subject_topic'],  # MOVE FROM OPTIONAL
    'subject': ['subject', 'subject_name'],  # ADD THIS
}

# Validate in parse_excel_rows
topic_name = row[headers['topic_name']]
if not topic_name or str(topic_name).strip() == '':
    raise UploadValidationError(f"Row {row_idx}: Topic name is empty")
```

### ✅ Issue 3: Chapter Field
**Current State:**
- Chapter is optional in both Topic model and parser
- Not parsed from Excel at all

**Recommendation:**
- Keep as optional but ADD to parser for future use:
```python
OPTIONAL_COLUMNS = {
    # ... existing
    'chapter': ['chapter', 'chapter_name', 'chapter_number'],
}

# In get_or_create_topic
chapter = q_data.get('chapter')  # Pass from question data
topic, created = Topic.objects.get_or_create(
    name=topic_name,
    subject=subject,
    defaults={
        'icon': '📚',
        'chapter': chapter  # Set if provided
    }
)
```

## Recommended Changes Summary

### 1. Update Excel Format Documentation
**Add to REQUIRED columns:**
- `topic_name` - REQUIRED (currently optional)
- `subject` - REQUIRED (currently not parsed)

### 2. Update Parser Code (`institution_upload.py`)

```python
# Change REQUIRED_COLUMNS
REQUIRED_COLUMNS = {
    'question_text': ['question_text', 'question', 'q', 'question_stem'],
    'option_a': ['option_a', 'a', 'option1'],
    'option_b': ['option_b', 'b', 'option2'],
    'option_c': ['option_c', 'c', 'option3'],
    'option_d': ['option_d', 'd', 'option4'],
    'correct_answer': ['correct_answer', 'answer', 'correct', 'correct_option'],
    'explanation': ['explanation', 'explain', 'solution'],
    'topic_name': ['topic_name', 'topic', 'subject_topic'],  # MOVED FROM OPTIONAL
    'subject': ['subject', 'subject_name'],  # ADDED
}

OPTIONAL_COLUMNS = {
    'difficulty': ['difficulty', 'level', 'difficulty_level'],
    'question_type': ['question_type', 'type', 'q_type'],
    'chapter': ['chapter', 'chapter_name', 'chapter_number'],  # ADDED
}
```

**Update `get_or_create_topic` signature:**
```python
def get_or_create_topic(
    topic_name: str, 
    subject: str,  # ADDED - explicit subject
    exam_type: str, 
    institution: Institution,
    chapter: str = None  # ADDED - optional chapter
) -> Topic:
    """Create or get topic with explicit subject."""
    
    # Validate subject
    valid_subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
    if subject not in valid_subjects:
        raise UploadValidationError(
            f"Invalid subject: {subject}. Must be one of: {', '.join(valid_subjects)}"
        )
    
    # Create/get topic
    topic, created = Topic.objects.get_or_create(
        name=topic_name.strip(),
        subject=subject,
        chapter=chapter,  # Include chapter in lookup
        defaults={'icon': '📚'}
    )
    
    return topic
```

**Update `parse_excel_rows`:**
```python
# Extract and validate topic_name
topic_name = row[headers['topic_name']]
if not topic_name or str(topic_name).strip() == '':
    raise UploadValidationError(f"Row {row_idx}: Topic name is empty")

# Extract and validate subject
subject = row[headers['subject']]
if not subject or str(subject).strip() == '':
    raise UploadValidationError(f"Row {row_idx}: Subject is empty")

# Normalize and validate subject
subject = str(subject).strip()
# Handle common variations
subject_map = {
    'physics': 'Physics',
    'chemistry': 'Chemistry',
    'botany': 'Botany',
    'biology': 'Botany',  # Map biology to Botany
    'zoology': 'Zoology',
}
subject_lower = subject.lower()
if subject_lower in subject_map:
    subject = subject_map[subject_lower]
else:
    # Try direct match with capitalized first letter
    subject = subject.capitalize()

valid_subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
if subject not in valid_subjects:
    raise UploadValidationError(
        f"Row {row_idx}: Invalid subject '{subject}'. "
        f"Must be one of: {', '.join(valid_subjects)}"
    )

# Extract optional chapter
chapter = None
if 'chapter' in headers:
    chapter_val = row[headers['chapter']]
    if chapter_val:
        chapter = str(chapter_val).strip()

# Get or create topic with explicit subject
topic = get_or_create_topic(
    topic_name=str(topic_name).strip(),
    subject=subject,
    exam_type=exam_type,
    institution=institution,
    chapter=chapter
)
```

## Updated Excel Template

### Download Template: `institution_test_template.xlsx`

**Sheet 1: Instructions**
```
NEET Ninja - Institution Test Upload Template

Instructions:
1. Use Sheet 2 (Questions) to enter your questions
2. Fill all REQUIRED columns (marked with *)
3. Optional columns can be left blank
4. Do not modify column headers
5. Maximum 5000 questions per file
6. File size limit: 10 MB

Required Columns (Must Have Values):
- question_text*: The question text
- option_a*, option_b*, option_c*, option_d*: Four answer options
- correct_answer*: Must be A, B, C, or D
- explanation*: Explanation for the correct answer
- topic_name*: Name of the topic/concept
- subject*: Must be Physics, Chemistry, Botany, or Zoology

Optional Columns:
- difficulty: Easy, Moderate, or Hard
- question_type: Type of question (e.g., Conceptual, Numerical)
- chapter: Chapter name or number
```

**Sheet 2: Questions (Template)**

| question_text* | option_a* | option_b* | option_c* | option_d* | correct_answer* | explanation* | topic_name* | subject* | difficulty | question_type | chapter |
|----------------|-----------|-----------|-----------|-----------|-----------------|--------------|-------------|----------|------------|---------------|---------|
| Sample question 1 | Option A | Option B | Option C | Option D | A | Explanation here | Topic Name | Physics | Easy | Conceptual | Chapter 1 |
| Sample question 2 | Option A | Option B | Option C | Option D | B | Explanation here | Another Topic | Chemistry | Moderate | Numerical | Chapter 2 |

## Validation Error Messages

Users will receive clear error messages for:
- Missing required columns
- Empty required fields
- Invalid correct_answer format
- Invalid subject values
- File size exceeded
- Maximum rows exceeded
- Invalid Excel format

## Success Response Format

```json
{
    "success": true,
    "test_id": 123,
    "test_code": "INST_1_NEET_20250106120000_abc12345",
    "test_name": "Weekly Mock Test 1",
    "questions_created": 150,
    "topics_used": ["Newton's Laws", "Thermodynamics", "Photosynthesis"],
    "exam_type": "neet"
}
```

## Implementation Status

### ✅ Completed
- Excel parser with column name variants
- File size and row count validation
- Correct answer normalization
- Transaction-safe upload
- Topic and Question creation
- PlatformTest generation

### ⚠️ Needs Fixing
- [ ] Make `topic_name` REQUIRED (move from optional)
- [ ] Add `subject` as REQUIRED column
- [ ] Remove subject inference logic (unreliable)
- [ ] Update `get_or_create_topic` to accept explicit subject
- [ ] Add chapter parsing (optional)
- [ ] Update frontend upload UI to show new required fields
- [ ] Create Excel template file with instructions

### 📋 Recommended Enhancements
- [ ] Add bulk validation preview (show parsed data before saving)
- [ ] Support multiple subjects per question (array field)
- [ ] Add image upload support for diagrams
- [ ] Add question tagging system
- [ ] Export questions back to Excel
- [ ] Duplicate question detection

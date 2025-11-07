# Institution Test Upload - Quick Reference Guide

## 📋 Required Excel Columns

### ✅ Must-Have Columns (9 Required)

| # | Column Name | Example Value | Notes |
|---|-------------|---------------|-------|
| 1 | **question_text** | "What is the SI unit of force?" | The question stem |
| 2 | **option_a** | "Newton" | First answer option |
| 3 | **option_b** | "Joule" | Second answer option |
| 4 | **option_c** | "Watt" | Third answer option |
| 5 | **option_d** | "Pascal" | Fourth answer option |
| 6 | **correct_answer** | "A" | Must be A, B, C, or D |
| 7 | **explanation** | "Newton is the SI unit of force..." | Answer explanation |
| 8 | **topic_name** | "Newton's Laws of Motion" | Topic/concept name |
| 9 | **subject** | "Physics" | Must be: Physics, Chemistry, Botany, or Zoology |

### ⚙️ Optional Columns (3)

| # | Column Name | Example Value | Notes |
|---|-------------|---------------|-------|
| 1 | **difficulty** | "Easy" | Easy, Moderate, or Hard |
| 2 | **question_type** | "Conceptual" | Any text value |
| 3 | **chapter** | "Chapter 5" | Chapter name/number |

## 📊 Data Flow Diagram

```
Excel File Upload
       ↓
┌──────────────────────┐
│  File Validation     │
│  - Size check        │
│  - Format check      │
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Header Parsing      │
│  - Map column names  │
│  - Validate required │
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Row Parsing         │
│  - Extract values    │
│  - Validate data     │
│  - Normalize answers │
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Topic Creation      │
│  topic_name + subject│
│  + chapter           │
│  → Topic.objects     │
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Question Creation   │
│  Link to Topic       │
│  Set institution     │
│  → Question.objects  │
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Test Creation       │
│  Generate test_code  │
│  Link questions      │
│  → PlatformTest      │
└──────────────────────┘
       ↓
    Success Response
```

## 🔄 Database Schema Relationships

```
Institution
    ├─→ InstitutionAdmin (one-to-many)
    ├─→ PlatformTest (one-to-many, institution tests)
    ├─→ Question (one-to-many, institution questions)
    └─→ StudentProfile (one-to-many, students linked to institution)

Topic (Independent)
    ├── name (required)
    ├── subject (required) ← Must be Physics, Chemistry, Botany, or Zoology
    ├── icon (required)
    └── chapter (optional)

Question
    ├── topic (FK to Topic) ← Created/linked during upload
    ├── question (text)
    ├── option_a/b/c/d
    ├── correct_answer
    ├── explanation
    ├── difficulty (optional)
    ├── question_type (optional)
    ├── institution (FK) ← Set during upload
    ├── institution_test_name ← Set during upload
    └── exam_type ← Set during upload

PlatformTest
    ├── test_name
    ├── test_code (auto-generated)
    ├── selected_topics (array of Topic IDs)
    ├── total_questions
    ├── time_limit
    ├── is_institution_test = True
    ├── institution (FK)
    └── exam_type
```

## 🎯 Subject Classification Logic

### Before Fix (Unreliable - Keyword Inference)
```python
# ❌ Old Logic
if 'physics' in topic_name.lower():
    subject = 'Physics'
elif 'chemistry' in topic_name.lower():
    subject = 'Chemistry'
# ... more keyword matching
```

**Problems:**
- Topic name: "Laws of Motion" → No keyword match → Wrong subject
- Topic name: "Chemical Reactions in Physics" → Matches "chemical" → Wrong subject
- Unreliable and error-prone

### After Fix (Explicit Subject Column)
```python
# ✅ New Logic
subject = row[headers['subject']]  # Read from Excel
subject = normalize_subject(subject)  # Handle variations
validate_subject(subject)  # Must be Physics/Chemistry/Botany/Zoology
topic = create_topic(topic_name, subject, chapter)
```

**Benefits:**
- Explicit and accurate
- User controls classification
- Validation ensures correctness
- Supports analytics and scoring

## 📝 Sample Excel Data

### Minimal Example (9 Required Columns)

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject |
|---------------|----------|----------|----------|----------|----------------|-------------|------------|---------|
| What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton (N) is the SI unit of force | Newton's Laws | Physics |
| Which gas is released during photosynthesis? | Oxygen | Carbon dioxide | Nitrogen | Hydrogen | A | Plants release O₂ during photosynthesis | Photosynthesis | Botany |

### Complete Example (All 12 Columns)

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject | difficulty | question_type | chapter |
|---------------|----------|----------|----------|----------|----------------|-------------|------------|---------|------------|---------------|---------|
| What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton (N) is the SI unit of force | Newton's Laws | Physics | Easy | Conceptual | Chapter 5 |
| Which gas is released during photosynthesis? | Oxygen | Carbon dioxide | Nitrogen | Hydrogen | A | Plants release O₂ | Photosynthesis | Botany | Easy | Knowledge | Chapter 2 |
| Calculate acceleration if F=10N, m=2kg | 5 m/s² | 10 m/s² | 20 m/s² | 0.5 m/s² | A | Using F=ma, a=F/m=10/2=5 | Newton's Laws | Physics | Moderate | Numerical | Chapter 5 |

## ✅ Parser Validation Checklist

### File Level
- [ ] File size ≤ 10 MB
- [ ] Valid Excel format (.xlsx, .xls)
- [ ] At least one sheet present
- [ ] Header row exists (Row 1)

### Column Level
- [ ] All 9 required columns present
- [ ] Column names match accepted variants
- [ ] Optional columns recognized if present

### Row Level (Per Question)
- [ ] question_text: Not empty
- [ ] option_a/b/c/d: All four present and not empty
- [ ] correct_answer: Valid format (A/B/C/D or variants)
- [ ] explanation: Not empty
- [ ] topic_name: Not empty
- [ ] subject: Not empty AND valid (Physics/Chemistry/Botany/Zoology)
- [ ] difficulty: If present, one of Easy/Moderate/Hard
- [ ] chapter: No validation (any text)

### Limits
- [ ] Total rows ≤ 5,000 questions
- [ ] No duplicate questions (same text + options + topic)

## 🚀 Upload Process Steps

### Frontend Flow
1. User selects Excel file
2. User selects exam type (NEET/JEE)
3. User enters test name
4. User sets time limit (optional, default 180 min)
5. Frontend sends multipart POST to `/api/institution-admin/upload/`

### Backend Processing
1. **Authentication**: Verify institution admin JWT token
2. **File Validation**: Check size and format
3. **Parsing**: Read Excel, map columns, validate headers
4. **Row Processing**: Extract and validate each question
5. **Topic Creation**: Create/find Topic records with subject
6. **Question Creation**: Create Question records linked to topics
7. **Test Creation**: Create PlatformTest with auto-generated code
8. **Transaction Commit**: All-or-nothing database save
9. **Response**: Return test details and statistics

### Success Response
```json
{
    "success": true,
    "test_id": 123,
    "test_code": "INST_1_NEET_20250106120000_abc12345",
    "test_name": "Weekly Mock Test 1",
    "questions_created": 150,
    "topics_used": [
        "Newton's Laws",
        "Thermodynamics",
        "Photosynthesis",
        "Cell Structure"
    ],
    "exam_type": "neet"
}
```

### Error Response
```json
{
    "success": false,
    "error": "Row 45: Subject is required and cannot be empty"
}
```

## 🔧 Changes Made to Parser

### 1. Column Configuration Updated
```python
# BEFORE
OPTIONAL_COLUMNS = {
    'topic_name': [...],  # Was optional
    # No subject column
}

# AFTER
REQUIRED_COLUMNS = {
    'topic_name': [...],  # Now required
    'subject': [...],     # Added as required
}

OPTIONAL_COLUMNS = {
    'chapter': [...],     # Added as optional
}
```

### 2. Function Signature Updated
```python
# BEFORE
def get_or_create_topic(topic_name, exam_type, institution):
    # Inferred subject from keywords

# AFTER
def get_or_create_topic(topic_name, subject, exam_type, institution, chapter=None):
    # Explicit subject validation
    # Chapter support added
```

### 3. Row Parsing Enhanced
```python
# BEFORE
topic_name = None  # Optional
if 'topic_name' in headers:
    topic_name = row[headers['topic_name']]
# No subject parsing

# AFTER
topic_name = row[headers['topic_name']]  # Required
if not topic_name:
    raise ValidationError("Topic name required")

subject = row[headers['subject']]  # Required
subject = normalize_subject(subject)  # Handle variations
validate_subject(subject)  # Must be valid

chapter = row[headers['chapter']] if 'chapter' in headers else None
```

### 4. Subject Normalization Added
```python
subject_map = {
    'physics': 'Physics',
    'chemistry': 'Chemistry',
    'botany': 'Botany',
    'biology': 'Botany',          # Map to Botany
    'plant biology': 'Botany',
    'zoology': 'Zoology',
    'animal biology': 'Zoology',
}

valid_subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
```

## 📊 Why These Changes Matter

### 1. Data Integrity
- **Before**: Generic topics like "Institution - NEET Questions"
- **After**: Specific topics like "Newton's Laws" with subject "Physics"

### 2. Analytics Accuracy
- **TestSession** tracks subject-wise topics:
  - `physics_topics`, `chemistry_topics`, `botany_topics`, `zoology_topics`
- **TestSession** calculates subject-wise scores:
  - `physics_score`, `chemistry_score`, `botany_score`, `zoology_score`
- **Requires**: Accurate subject classification from Topic model

### 3. Student Experience
- Topic-wise performance tracking
- Subject-wise weak area identification
- Personalized study recommendations
- Accurate insights generation

### 4. Question Selection
- Selection engine uses topic and subject for:
  - Filtering questions by subject
  - Balanced subject distribution
  - Avoiding repeated topics

## 🎓 Usage Instructions for Institutions

### Step 1: Prepare Excel File
1. Download template (if available)
2. Fill all 9 required columns
3. Use correct subject names: Physics, Chemistry, Botany, or Zoology
4. Optionally add difficulty, question_type, chapter

### Step 2: Upload via Dashboard
1. Login to institution admin dashboard
2. Select exam type (NEET or JEE)
3. Enter test name
4. Set time limit (default 180 minutes)
5. Choose Excel file
6. Click "Upload Test"

### Step 3: Verify Upload
1. Check success message with test code
2. Review number of questions created
3. View list of topics used
4. Test is automatically set to active

### Step 4: Share with Students
1. Give students the institution code
2. Students link to institution via code
3. Students see institution tests in their test list
4. Students start test like any platform test

## 🔍 Testing the Parser

### Test Case 1: Valid Upload
**Excel:**
- 100 questions
- All required columns filled
- Valid subjects (Physics, Chemistry, Botany, Zoology)
- Mix of difficulties

**Expected:**
- ✅ Success response
- ✅ 100 questions created
- ✅ Topics created with correct subjects
- ✅ Test created and activated

### Test Case 2: Missing Subject Column
**Excel:**
- Missing 'subject' column

**Expected:**
- ❌ Error: "Missing required columns: subject"

### Test Case 3: Empty Subject Values
**Excel:**
- Subject column present but some rows empty

**Expected:**
- ❌ Error: "Row X: Subject is required and cannot be empty"

### Test Case 4: Invalid Subject Values
**Excel:**
- Subject = "Mathematics" (not valid)

**Expected:**
- ❌ Error: "Row X: Invalid subject 'Mathematics'. Must be one of: Physics, Chemistry, Botany, Zoology"

### Test Case 5: Subject Variations
**Excel:**
- Subjects: "physics", "CHEMISTRY", "Biology", "Zoology"

**Expected:**
- ✅ Normalized to: Physics, Chemistry, Botany, Zoology

## 📚 Additional Resources

- **Full Specification**: See `EXCEL_FORMAT_SPECIFICATION.md`
- **Parser Code**: `backend/neet_app/services/institution_upload.py`
- **Models**: `backend/neet_app/models.py`
- **Upload Endpoint**: `backend/neet_app/views/institution_admin_views.py`
- **Frontend Dashboard**: `client/src/pages/institution-admin-dashboard.tsx`

## 🆘 Common Issues & Solutions

### Issue: "Missing required columns"
**Solution**: Ensure Excel has all 9 required column names (use accepted variants)

### Issue: "Invalid subject"
**Solution**: Use only: Physics, Chemistry, Botany, or Zoology

### Issue: "Topic name is empty"
**Solution**: Fill topic_name for every question row

### Issue: "File size exceeds limit"
**Solution**: Split into multiple files (max 5000 questions per file)

### Issue: "Correct answer format invalid"
**Solution**: Use A, B, C, or D (or accepted variants like 1, 2, 3, 4)

---

**Last Updated**: 2025-01-06  
**Parser Version**: 2.0 (With explicit subject requirement)

# Excel Template Structure for Institution Test Upload

## File: institution_test_template.xlsx

### Sheet 1: Instructions

```
╔════════════════════════════════════════════════════════════════════════╗
║           NEET Ninja - Institution Test Upload Template               ║
║                          Instructions                                  ║
╚════════════════════════════════════════════════════════════════════════╝

📋 HOW TO USE THIS TEMPLATE:
1. Use Sheet 2 (Questions) to enter your questions
2. Fill ALL required columns (marked with *)
3. Optional columns can be left blank
4. Do not modify column headers
5. Maximum 5000 questions per file
6. File size limit: 10 MB

✅ REQUIRED COLUMNS (Must Have Values):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Column Name          Description                       Example
───────────────────────────────────────────────────────────────────────
question_text*       The question text                "What is the SI unit of force?"
option_a*            First answer option              "Newton"
option_b*            Second answer option             "Joule"  
option_c*            Third answer option              "Watt"
option_d*            Fourth answer option             "Pascal"
correct_answer*      Correct option (A/B/C/D)        "A"
explanation*         Explanation for answer           "Newton is the SI unit..."
topic_name*          Name of topic/concept            "Newton's Laws of Motion"
subject*             Subject classification           "Physics"

⚙️ OPTIONAL COLUMNS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Column Name          Description                       Example
───────────────────────────────────────────────────────────────────────
difficulty           Question difficulty level        "Easy" | "Moderate" | "Hard"
question_type        Type of question                 "Conceptual" | "Numerical"
chapter              Chapter name or number           "Chapter 5" | "Ch. 5"

📌 IMPORTANT NOTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBJECT VALUES (Case-insensitive):
  ✓ Physics          - For Physics questions
  ✓ Chemistry        - For Chemistry questions
  ✓ Botany           - For Botany/Plant Biology questions
  ✓ Zoology          - For Zoology/Animal Biology questions
  
  Note: "Biology" will automatically map to "Botany"

CORRECT ANSWER FORMATS (All acceptable):
  ✓ Single letter:   A, B, C, D
  ✓ Numbers:         1, 2, 3, 4  (1=A, 2=B, 3=C, 4=D)
  ✓ Full text:       OPTION_A, OPTION A, Option A
  ✓ Words:           FIRST, SECOND, THIRD, FOURTH

COLUMN NAME VARIATIONS (Parser accepts these):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Standard Name    Accepted Variations
───────────────────────────────────────────────────────────────────────
question_text    question, q, question_stem
option_a         a, option1
option_b         b, option2
option_c         c, option3
option_d         d, option4
correct_answer   answer, correct, correct_option
explanation      explain, solution
topic_name       topic, subject_topic
subject          subject_name
difficulty       level, difficulty_level
question_type    type, q_type
chapter          chapter_name, chapter_number

❌ COMMON MISTAKES TO AVOID:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ Leaving required columns empty
✗ Using invalid subject names (e.g., "Maths", "Bio")
✗ Wrong correct_answer format (e.g., "option A" instead of "A")
✗ Deleting or renaming column headers
✗ Exceeding 5000 questions per file
✗ File size over 10 MB

📞 SUPPORT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If you encounter any issues:
1. Check this instructions sheet
2. Verify all required columns are filled
3. Ensure subject values are correct (Physics/Chemistry/Botany/Zoology)
4. Contact support with error message

╔════════════════════════════════════════════════════════════════════════╗
║                 Now proceed to Sheet 2 → Questions                     ║
╚════════════════════════════════════════════════════════════════════════╝
```

---

### Sheet 2: Questions (Template)

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                    QUESTION ENTRY SHEET                                                                               ║
║  Fill the rows below with your questions. Each row represents one question. Sample questions are provided for reference - DELETE THEM before upload. ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

**Column Headers (Row 1):**

| question_text* | option_a* | option_b* | option_c* | option_d* | correct_answer* | explanation* | topic_name* | subject* | difficulty | question_type | chapter |
|----------------|-----------|-----------|-----------|-----------|-----------------|--------------|-------------|----------|------------|---------------|---------|

**Sample Data (Rows 2-6):**

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject | difficulty | question_type | chapter |
|---------------|----------|----------|----------|----------|----------------|-------------|------------|---------|------------|---------------|---------|
| What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton (N) is the SI unit of force, defined as kg⋅m/s². One Newton is the force required to accelerate 1 kg mass at 1 m/s². | Newton's Laws of Motion | Physics | Easy | Conceptual | Chapter 5 |
| Which organ in plants performs photosynthesis? | Root | Stem | Leaf | Flower | C | Leaves contain chlorophyll in their chloroplasts, which captures sunlight and converts CO₂ and H₂O into glucose and oxygen through photosynthesis. | Photosynthesis | Botany | Easy | Knowledge | Chapter 2 |
| Calculate the acceleration if a force of 10 N is applied to a 2 kg mass. | 5 m/s² | 10 m/s² | 20 m/s² | 0.5 m/s² | A | Using Newton's Second Law: F = ma. Therefore, a = F/m = 10 N / 2 kg = 5 m/s². | Newton's Laws of Motion | Physics | Moderate | Numerical | Chapter 5 |
| Which of the following is an inert gas? | Oxygen | Nitrogen | Helium | Hydrogen | C | Helium is a noble gas (Group 18) with complete outer electron shell, making it chemically inert and non-reactive under normal conditions. | Periodic Table | Chemistry | Easy | Knowledge | Chapter 3 |
| What is the function of mitochondria? | Photosynthesis | Protein synthesis | Energy production | Cell division | C | Mitochondria are the powerhouses of the cell, producing ATP through cellular respiration. They convert glucose and oxygen into energy (ATP), CO₂, and H₂O. | Cell Organelles | Zoology | Moderate | Conceptual | Chapter 1 |

**Instructions for Data Entry:**

```
┌────────────────────────────────────────────────────────────────────┐
│  ✏️ FILLING THE TEMPLATE:                                          │
├────────────────────────────────────────────────────────────────────┤
│  1. DELETE the 5 sample question rows above                        │
│  2. Start entering your questions from Row 2                       │
│  3. Each row = 1 question                                          │
│  4. Fill all columns marked with * (required)                      │
│  5. Leave optional columns blank if not needed                     │
│  6. Copy rows down to add more questions (max 5000)                │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  💡 TIPS FOR QUALITY QUESTIONS:                                    │
├────────────────────────────────────────────────────────────────────┤
│  • Write clear, unambiguous questions                              │
│  • Ensure all 4 options are plausible                              │
│  • Provide detailed explanations with reasoning                    │
│  • Use consistent topic names for related questions                │
│  • Group questions by chapter when possible                        │
│  • Mix difficulty levels (Easy, Moderate, Hard)                    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  🔍 BEFORE UPLOADING:                                              │
├────────────────────────────────────────────────────────────────────┤
│  ✓ All required columns filled (no empty cells in *)               │
│  ✓ Subjects are: Physics, Chemistry, Botany, or Zoology            │
│  ✓ Correct answers are A, B, C, or D                               │
│  ✓ Explanations are clear and detailed                             │
│  ✓ Topic names are consistent across related questions             │
│  ✓ File size under 10 MB                                           │
│  ✓ Question count under 5000                                       │
└────────────────────────────────────────────────────────────────────┘
```

---

### Sheet 3: Subject Distribution Template (Optional)

```
╔════════════════════════════════════════════════════════════════════════╗
║                    SUBJECT DISTRIBUTION PLANNING                       ║
║                        (Reference Only)                                ║
╚════════════════════════════════════════════════════════════════════════╝

Use this sheet to plan your question distribution across subjects.
This sheet is NOT parsed - it's for your planning only.

NEET PATTERN (180 questions, 3 hours):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Subject          Questions    Marks    Recommended Distribution
──────────────────────────────────────────────────────────────────────
Physics          45           180      Easy: 15, Moderate: 20, Hard: 10
Chemistry        45           180      Easy: 15, Moderate: 20, Hard: 10
Botany           45           180      Easy: 15, Moderate: 20, Hard: 10
Zoology          45           180      Easy: 15, Moderate: 20, Hard: 10
──────────────────────────────────────────────────────────────────────
TOTAL            180          720      Easy: 60, Moderate: 80, Hard: 40

YOUR TEST PLANNING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Subject          Questions    Easy    Moderate    Hard    Topics Covered
──────────────────────────────────────────────────────────────────────────
Physics          ____         ____    ____        ____    ________________
Chemistry        ____         ____    ____        ____    ________________
Botany           ____         ____    ____        ____    ________________
Zoology          ____         ____    ____        ____    ________________
──────────────────────────────────────────────────────────────────────────
TOTAL            ____         ____    ____        ____

TOPIC DISTRIBUTION CHECKLIST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Physics Topics:
□ Mechanics (Kinematics, Dynamics, Laws of Motion)
□ Thermodynamics
□ Waves and Oscillations
□ Electromagnetism
□ Optics
□ Modern Physics

Chemistry Topics:
□ Physical Chemistry (Thermodynamics, Kinetics)
□ Inorganic Chemistry (Periodic Table, Coordination)
□ Organic Chemistry (Hydrocarbons, Reactions)

Botany Topics:
□ Plant Physiology
□ Plant Anatomy
□ Cell Biology
□ Genetics
□ Ecology

Zoology Topics:
□ Animal Physiology
□ Human Physiology
□ Evolution
□ Genetics
□ Ecology
```

---

### Sheet 4: Validation Checklist

```
╔════════════════════════════════════════════════════════════════════════╗
║                      PRE-UPLOAD VALIDATION CHECKLIST                   ║
╚════════════════════════════════════════════════════════════════════════╝

Before uploading your Excel file, complete this checklist:

FILE CHECKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ File format is .xlsx or .xls
□ File size is under 10 MB
□ Sheet "Questions" exists and is filled
□ Sample questions have been deleted
□ No hidden rows or columns

COLUMN CHECKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ All 9 required column headers present
□ Column headers are in Row 1
□ No typos in column names
□ Optional columns (if used) have correct names

DATA QUALITY CHECKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ No empty cells in required columns (*)
□ All questions have complete text (no truncated questions)
□ All 4 options provided for every question
□ Explanations are detailed (not just one word)
□ Topic names are consistent (same spelling/capitalization)
□ Subject values are ONLY: Physics, Chemistry, Botany, Zoology

ANSWER CHECKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Correct answers are A, B, C, or D (or accepted variants)
□ Each question has exactly ONE correct answer
□ Correct answer matches one of the four options

OPTIONAL FIELD CHECKS (if used):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Difficulty values are: Easy, Moderate, or Hard
□ Question types are consistent in format
□ Chapter information is uniform (e.g., all "Chapter X" or all "Ch. X")

QUANTITY CHECKS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Total questions: _____ (must be ≤ 5000)
□ Physics questions: _____
□ Chemistry questions: _____
□ Botany questions: _____
□ Zoology questions: _____

FINAL REVIEW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Reviewed first 10 questions for quality
□ Spot-checked random questions throughout
□ Verified no duplicate questions
□ Confirmed subject distribution matches plan
□ Test name decided: _________________________________
□ Time limit decided: _______ minutes (default: 180)

╔════════════════════════════════════════════════════════════════════════╗
║  ✅ All checks complete? You're ready to upload!                      ║
╚════════════════════════════════════════════════════════════════════════╝

UPLOAD STEPS:
1. Login to Institution Admin Dashboard
2. Select Exam Type (NEET/JEE)
3. Enter Test Name
4. Set Time Limit (optional)
5. Choose this Excel file
6. Click "Upload Test"
7. Wait for success confirmation
8. Note down the Test Code provided
9. Share institution code with students

Need help? Refer to Sheet 1 (Instructions) or contact support.
```

---

## File Structure Summary

```
institution_test_template.xlsx
├── Sheet 1: Instructions (Read First)
│   └── Detailed usage guide, column specifications, examples
├── Sheet 2: Questions (Data Entry)
│   └── Column headers + sample questions (delete samples before upload)
├── Sheet 3: Subject Distribution (Planning Tool)
│   └── Optional planning sheet for question distribution
└── Sheet 4: Validation Checklist (Pre-Upload)
    └── Checklist to verify data quality before upload
```

## Color Coding (Recommended)

- **Header Row (Row 1)**: Bold, Blue background, White text
- **Required Columns**: Yellow highlight in header
- **Sample Questions**: Light gray background (to indicate deletion needed)
- **Instructions Sheet**: Blue headers, organized sections

## Cell Formatting

- **question_text**: Wrap text, Left aligned
- **options (a/b/c/d)**: Wrap text, Left aligned
- **correct_answer**: Center aligned, Bold
- **explanation**: Wrap text, Left aligned
- **topic_name**: Left aligned
- **subject**: Center aligned, Dropdown list (Physics, Chemistry, Botany, Zoology)
- **difficulty**: Center aligned, Dropdown list (Easy, Moderate, Hard)

## Excel Formula Validations (Optional Enhancement)

```excel
For 'subject' column: Data Validation List
= Physics,Chemistry,Botany,Zoology

For 'correct_answer' column: Data Validation List
= A,B,C,D

For 'difficulty' column: Data Validation List
= Easy,Moderate,Hard
```

This prevents users from entering invalid values and reduces errors during upload.

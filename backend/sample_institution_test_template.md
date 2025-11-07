# Sample Excel Template for Institution Test Upload

## File Format: Excel (.xlsx)

Create an Excel file with the following column headers in the first row:

---

## Required Columns

| Column Name | Description | Example | Notes |
|-------------|-------------|---------|-------|
| **question_text** | The question text | "What is the SI unit of force?" | Can be multi-line |
| **option_a** | First option | "Newton" | Required |
| **option_b** | Second option | "Joule" | Required |
| **option_c** | Third option | "Watt" | Required |
| **option_d** | Fourth option | "Pascal" | Required |
| **correct_answer** | Correct option | "A" or "Option A" or "1" | A/B/C/D, 1/2/3/4, or Option A/B/C/D |
| **explanation** | Detailed explanation | "Newton is the SI unit of force (F=ma)" | Shown after answer |

---

## Optional Columns

| Column Name | Description | Example | Default if omitted |
|-------------|-------------|---------|-------------------|
| **topic_name** | Subject/topic | "Physics - Laws of Motion" | Auto-created or "General" |
| **difficulty** | Question difficulty | "Easy", "Moderate", or "Hard" | "Moderate" |
| **question_type** | Type of question | "Conceptual", "Numerical", etc. | "Multiple Choice" |

---

## Sample Excel Template

### Row 1 (Headers):
```
question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | difficulty
```

### Row 2 (Example Question 1):
```
What is the SI unit of force? | Newton | Joule | Watt | Pascal | A | Newton is the SI unit of force, defined as kg⋅m/s². It is named after Isaac Newton. | Physics - Units and Measurements | Easy
```

### Row 3 (Example Question 2):
```
The process by which plants make their food is called: | Respiration | Photosynthesis | Transpiration | Germination | B | Photosynthesis is the process by which green plants use sunlight to synthesize food from carbon dioxide and water. Chlorophyll is the key pigment involved. | Biology - Plant Physiology | Easy
```

### Row 4 (Example Question 3):
```
What is the molecular formula of glucose? | C₆H₁₂O₆ | C₁₂H₂₂O₁₁ | C₆H₁₀O₅ | CH₃COOH | A | Glucose is a simple sugar with the molecular formula C₆H₁₂O₆. It is the primary source of energy for cells. | Chemistry - Organic Chemistry | Moderate
```

---

## Validation Rules

### File Constraints:
- ✅ Maximum file size: **10 MB**
- ✅ Maximum questions per file: **5000**
- ✅ File format: **.xlsx** (Excel 2007+)

### Question Constraints:
- ✅ All four options (A, B, C, D) must be provided
- ✅ Correct answer must be one of: A, B, C, D
- ✅ Question text cannot be empty
- ✅ Explanation should be provided (recommended)

### Column Name Variations:
The system accepts multiple variations for column names:

**For question_text:**
- question_text, question, q, question_stem

**For options:**
- option_a, a, option1, option_1
- option_b, b, option2, option_2
- (similarly for C and D)

**For correct_answer:**
- correct_answer, answer, correct, correct_option

**For explanation:**
- explanation, explain, solution

---

## Correct Answer Formats

The system automatically normalizes these formats:

| Format | Example | Normalized To |
|--------|---------|---------------|
| Letter | A, B, C, D | A, B, C, D |
| Number | 1, 2, 3, 4 | A, B, C, D |
| Option Text | Option A, Option B | A, B, C, D |
| Full Text | FIRST, SECOND, THIRD, FOURTH | A, B, C, D |

---

## Creating Your Test File

### Step 1: Open Excel
Create a new Excel workbook (.xlsx format)

### Step 2: Add Headers
In the first row, add all required column headers:
```
question_text | option_a | option_b | option_c | option_d | correct_answer | explanation
```

### Step 3: Add Questions
Starting from row 2, add one question per row with all required information.

### Step 4: Add Optional Columns (Recommended)
Add `topic_name` and `difficulty` columns for better organization.

### Step 5: Save
Save as `.xlsx` format.

---

## Upload Instructions

### Via API (for developers):
```bash
curl -X POST http://localhost:8000/api/institution-admin/upload/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@your_questions.xlsx" \
  -F "test_name=Sample NEET Test" \
  -F "exam_type=neet" \
  -F "time_limit=180"
```

### Via Admin Dashboard (coming soon):
1. Login to institution admin dashboard
2. Click "Upload Test"
3. Select exam type (NEET/JEE)
4. Enter test name
5. Set time limit (in minutes)
6. Upload Excel file
7. Submit

---

## Common Errors and Solutions

### Error: "Invalid column headers"
**Solution**: Ensure first row contains required column names (case-insensitive)

### Error: "Correct answer must be A, B, C, or D"
**Solution**: Check the correct_answer column. Valid values: A, B, C, D, 1, 2, 3, 4, Option A/B/C/D

### Error: "Missing required option"
**Solution**: All four options (A, B, C, D) must be filled for every question

### Error: "File size exceeds limit"
**Solution**: File must be under 10MB. Split into multiple tests if needed.

### Error: "Too many questions"
**Solution**: Maximum 5000 questions per upload. Split into multiple tests.

---

## Tips for Best Results

1. **Use Clear Question Text**: Write questions clearly without ambiguity
2. **Provide Detailed Explanations**: Help students learn from their mistakes
3. **Organize by Topics**: Use topic_name column to group questions
4. **Set Appropriate Difficulty**: Mark questions as Easy/Moderate/Hard
5. **Proofread**: Check spelling, grammar, and correct answers before upload
6. **Test Small First**: Upload 5-10 questions first to verify format works
7. **No Duplicate Questions**: System prevents duplicates based on question text

---

## Example Questions by Subject

### Physics Question:
```
Question: A body of mass 2 kg is moving with a velocity of 10 m/s. What is its kinetic energy?
Option A: 50 J
Option B: 100 J
Option C: 150 J
Option D: 200 J
Correct Answer: B
Explanation: Kinetic Energy = (1/2)mv² = (1/2)(2)(10²) = 100 J
Topic: Physics - Work, Energy and Power
Difficulty: Moderate
```

### Chemistry Question:
```
Question: What is the oxidation state of Cr in K₂Cr₂O₇?
Option A: +3
Option B: +6
Option C: +7
Option D: +2
Correct Answer: B
Explanation: In K₂Cr₂O₇, 2(+1) + 2x + 7(-2) = 0, solving gives x = +6
Topic: Chemistry - Redox Reactions
Difficulty: Moderate
```

### Biology Question:
```
Question: Which organelle is known as the powerhouse of the cell?
Option A: Nucleus
Option B: Mitochondria
Option C: Ribosome
Option D: Golgi apparatus
Correct Answer: B
Explanation: Mitochondria produce ATP through cellular respiration, providing energy to the cell
Topic: Biology - Cell Biology
Difficulty: Easy
```

---

## Download Sample Template

A sample Excel file with 10 example questions is available in the repository:
- File: `sample_institution_test.xlsx`
- Location: `backend/sample_data/`

You can use this as a starting template and replace the questions with your own.

---

## Support

For issues with file upload or validation errors, contact your platform administrator or check the API error response for detailed information.

**Last Updated**: November 6, 2025

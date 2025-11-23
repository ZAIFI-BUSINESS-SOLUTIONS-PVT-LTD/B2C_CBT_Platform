# JSON Question Update - Quick Start Guide

## For Institution Admins

### What This Feature Does
Update question fields (images, text, explanations, etc.) for existing tests using a JSON file.

### When to Use This
- Need to fix/update images in multiple questions
- Want to bulk-update explanations
- Need to correct question text or options
- Want to update any allowed field for multiple questions

---

## Step-by-Step Guide

### 1. Prepare Your JSON File

Create a JSON file (e.g., `updates.json`) with this structure:

```json
[
  {
    "question_id": 1,
    "column_name": "question_image",
    "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  },
  {
    "question_id": 2,
    "column_name": "explanation",
    "value": "This is the updated explanation text"
  },
  {
    "question_id": 3,
    "column_name": "option_a",
    "value": "Updated option A text"
  }
]
```

**Important:**
- `question_id`: Use 1, 2, 3, ... (the question's position in your test)
- `column_name`: Field to update (see allowed columns below)
- `value`: New value (base64 for images, text for others)

### 2. Know Your Allowed Columns

**Text Fields:**
- `question` - Main question text
- `option_a`, `option_b`, `option_c`, `option_d` - Answer options
- `correct_answer` - Correct answer (A/B/C/D or numeric)
- `explanation` - Explanation text
- `difficulty` - Difficulty level
- `question_type` - Type of question

**Image Fields:**
- `question_image` - Image for the question
- `option_a_image`, `option_b_image`, `option_c_image`, `option_d_image` - Images for options
- `explanation_image` - Image for explanation

### 3. Upload the File

1. **Login** to institution admin dashboard
2. **Click** "Upload JSON Updates" button (next to "Upload Answer Key")
3. **Enter** the exact test name (must match what you used during test creation)
4. **Select** your JSON file (.json, max 10MB)
5. **Click** "Upload JSON Updates"

### 4. Review Results

You'll see:
- ✅ Total records processed
- ✅ How many succeeded
- ⚠️ How many were skipped (with error details)
- 📊 The automatically calculated offset (for reference)

---

## How the Question ID Mapping Works

**You provide:** `question_id` as 1, 2, 3, ... (position in test)

**Backend automatically:**
1. Finds your test's first question ID in database (e.g., 1523)
2. Calculates offset: `1523 - 1 = 1522`
3. Maps your IDs: 
   - Your `question_id: 1` → Database ID `1523`
   - Your `question_id: 2` → Database ID `1524`
   - etc.

**You don't need to know or calculate the offset!**

---

## Image Format Requirements

### Option 1: Data URI (Recommended)
```json
{
  "question_id": 1,
  "column_name": "question_image",
  "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### Option 2: Raw Base64
```json
{
  "question_id": 1,
  "column_name": "question_image",
  "value": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

Both formats work! The backend automatically:
- Strips the `data:image/...;base64,` prefix if present
- Removes whitespace/newlines
- Validates the base64 payload
- Stores clean base64 in database

---

## Common Examples

### Example 1: Update Images for First 3 Questions

```json
[
  {
    "question_id": 1,
    "column_name": "question_image",
    "value": "data:image/png;base64,..."
  },
  {
    "question_id": 2,
    "column_name": "question_image",
    "value": "data:image/png;base64,..."
  },
  {
    "question_id": 3,
    "column_name": "question_image",
    "value": "data:image/png;base64,..."
  }
]
```

### Example 2: Update Multiple Fields for Same Question

```json
[
  {
    "question_id": 5,
    "column_name": "question",
    "value": "What is the velocity of light?"
  },
  {
    "question_id": 5,
    "column_name": "explanation",
    "value": "The speed of light in vacuum is 3 × 10^8 m/s"
  },
  {
    "question_id": 5,
    "column_name": "difficulty",
    "value": "Easy"
  }
]
```

### Example 3: Fix Options and Images

```json
[
  {
    "question_id": 10,
    "column_name": "option_a",
    "value": "Corrected option A text"
  },
  {
    "question_id": 10,
    "column_name": "option_a_image",
    "value": "data:image/png;base64,..."
  },
  {
    "question_id": 10,
    "column_name": "option_b",
    "value": "Corrected option B text"
  }
]
```

---

## Error Handling

### Common Errors and Solutions

**"No questions found for test"**
→ Check test name spelling (case-sensitive!)

**"Question not found"**
→ Verify question_id exists in your test (1-based numbering)

**"Invalid column name"**
→ Use only allowed column names (see list above)

**"Invalid base64 payload"**
→ Check your base64 encoding is correct

**"File too large"**
→ Keep JSON under 10MB (compress images if needed)

---

## Tips & Best Practices

✅ **DO:**
- Use descriptive test names
- Keep JSON files organized and named clearly
- Test with a small JSON (2-3 records) first
- Download the sample template to get started
- Save your JSON files for documentation

❌ **DON'T:**
- Mix up test names (must match exactly)
- Use 0-based indexing (start from 1!)
- Upload extremely large base64 images (compress first)
- Modify column names that aren't in the allowed list
- Skip validation - check your JSON format first

---

## Troubleshooting

### Issue: Some records skipped

**Check:**
1. Are question IDs sequential (1, 2, 3, ...)?
2. Do all question IDs exist in your test?
3. Are column names spelled correctly?
4. Is base64 valid for image fields?

### Issue: Wrong questions updated

**Check:**
1. Did you enter the correct test name?
2. Are you using 1-based question numbering?

### Issue: Upload fails immediately

**Check:**
1. Is file size under 10MB?
2. Is file extension `.json`?
3. Is JSON syntax valid? (Use a validator: jsonlint.com)

---

## Need Help?

1. **Download sample template** - Click the button on upload page
2. **Check error details** - Read the specific errors shown after upload
3. **Test with 1-2 records** - Start small to verify format
4. **Contact support** - If issues persist

---

## Quick Reference

| Field | Type | Example |
|-------|------|---------|
| `question_id` | Integer (1-based) | `1`, `2`, `3` |
| `column_name` | String | `"question_image"` |
| `value` | String | Text or base64 |

**File limits:** 10MB max, .json only

**Authentication:** Institution admin login required

**Route:** `/json-question-upload` from dashboard

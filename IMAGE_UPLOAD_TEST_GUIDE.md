# Image Upload Testing Guide

## Overview
The system now supports optional base64 images for questions, options, and explanations via Excel upload for institution tests.

## Excel Column Format

### New Optional Columns
Add these columns to your institution test Excel file (all are optional):

- `question_image` - Base64 image for the question
- `option_a_image` - Base64 image for option A
- `option_b_image` - Base64 image for option B  
- `option_c_image` - Base64 image for option C
- `option_d_image` - Base64 image for option D
- `explanation_image` - Base64 image for the explanation

### Accepted Formats
Each image column can contain:

1. **Raw base64 string**: `iVBORw0KGgoAAAANSUhEUgAA...`
2. **Full data URI**: `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...`
3. **Empty/null**: Leave blank if no image needed

## Backend Processing

### Upload Flow
1. Excel file is uploaded via institution portal
2. Parser extracts image columns (see `OPTIONAL_COLUMNS` in `institution_upload.py`)
3. Normalizes data URIs to raw base64 (strips `data:image/...;base64,` prefix)
4. Stores raw base64 in `Question` model TextField

### Database Storage
- Images stored as raw base64 strings in TextField columns
- Nullable - backward compatible with existing questions
- No size limit enforced (consider adding validation for production)

## Frontend Rendering

### Auto-Detection
The `normalizeImageSrc()` helper automatically handles:

1. **Raw base64**: Detects format (PNG/JPEG/GIF/SVG) and wraps as data URI
2. **Full data URI**: Returns as-is
3. **HTTP(S) URLs**: Returns as-is
4. **Null/empty**: Returns undefined (no image rendered)

### Where Images Display

#### During Test (`test-interface.tsx`)
- **Question image**: Below question text
- **Option images**: Beside each option text

#### Results Review (`question-review.tsx`)
- **Question image**: Below question text
- **Option images**: Beside each option
- **Explanation image**: Above explanation text

## Testing Steps

### 1. Prepare Test Image
Get a small test image as base64:

```bash
# Linux/Mac
base64 -i test-image.png

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("test-image.png"))

# Or use online tool: https://www.base64-image.de/
```

### 2. Create Test Excel
Add a question with image columns:

| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation | topic_name | subject | question_image |
|--------------|----------|----------|----------|----------|----------------|-------------|------------|---------|----------------|
| Which element is shown? | Iron | Magnesium | Manganese | Calcium | B | Magnesium is essential for chlorophyll | Plant Nutrition | Botany | iVBORw0KGgoAAAA... |

### 3. Upload via Institution Portal
1. Log in as institution admin
2. Navigate to test upload
3. Select Excel file with image columns
4. Upload and create test

### 4. Take Test as Student
1. Log in as student
2. Start the uploaded test
3. **Verify**: Question image displays below question text
4. **Verify**: Option images display (if provided)

### 5. Check Results Page
1. Submit test
2. View results
3. Navigate to "Review" tab
4. **Verify**: Question, option, and explanation images render

## Troubleshooting

### Image Not Displaying

**Check 1: Data in Database**
```python
# Django shell
python manage.py shell

from neet_app.models import Question
q = Question.objects.get(id=YOUR_QUESTION_ID)
print("Question image present:", bool(q.question_image))
print("First 50 chars:", q.question_image[:50] if q.question_image else "None")
```

**Check 2: Serializer Includes Field**
- Test session: `QuestionForTestSerializer` includes image fields
- Results: `detailed_answers` includes image fields in view

**Check 3: Frontend Receives Data**
- Open browser DevTools → Network tab
- Find API call to `/api/test-sessions/{id}/`
- Check response JSON has `questionImage`, `optionAImage`, etc. (camelCase)

**Check 4: Console Errors**
- Open browser DevTools → Console
- Look for image loading errors or React errors

### Common Issues

**Issue**: Broken image icon displayed
- **Cause**: Invalid base64 data or incorrect MIME type
- **Fix**: Verify base64 string is complete and valid

**Issue**: No image shows but data exists
- **Cause**: Frontend not calling `normalizeImageSrc()`
- **Fix**: Check imports and usage in components

**Issue**: Excel upload fails
- **Cause**: Column name mismatch
- **Fix**: Use exact column names: `question_image`, `option_a_image`, etc.

**Issue**: Base64 too long for Excel cell
- **Cause**: Excel has ~32K character limit per cell
- **Fix**: Use smaller images or external hosting

## Image Size Recommendations

For best performance:
- **Max dimensions**: 800x600 pixels
- **Max file size**: 100KB (before base64 encoding)
- **Format**: PNG or JPEG
- **Base64 size**: ~33% larger than original file

## Production Considerations

### Add Validation (Recommended)
```python
# In serializers.py or model clean()
MAX_BASE64_LENGTH = 200000  # ~150KB original

def validate_question_image(self, value):
    if value and len(value) > MAX_BASE64_LENGTH:
        raise ValidationError("Image too large (max 150KB)")
    return value
```

### Security
- Base64 images are safe (no code execution risk)
- Consider rate limiting on upload endpoint
- Monitor database size growth

### Performance
- Large base64 strings increase page load time
- Consider CDN/external hosting for production
- Add image optimization in upload pipeline

## Summary

✅ **Backend**: Excel parser extracts and normalizes image columns  
✅ **Database**: Raw base64 stored in nullable TextFields  
✅ **API**: Serializers return image fields (camelCase for frontend)  
✅ **Frontend**: Auto-detects format and renders conditionally  
✅ **Backward Compatible**: Existing tests without images unaffected

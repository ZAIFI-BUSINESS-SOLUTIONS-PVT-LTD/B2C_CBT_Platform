# 🔧 Troubleshooting: Images Not Showing (Broken Icon)

## Problem Description
Images show as broken icons (🖼️) instead of actual images in the test interface.

---

## 🔍 **Diagnostic Steps**

### Step 1: Check Browser Console
1. Open browser DevTools (F12)
2. Go to **Console** tab
3. Look for logs starting with `[normalizeImageSrc]` or `[Image Error]`

**What to look for:**
```
[normalizeImageSrc] Input length: 12345 First 50 chars: data:image/png;base64,iVBORw0KGgoAAAANSU...
[normalizeImageSrc] Already a data URI, returning as-is
[Image Success] Question image loaded successfully  ← GOOD!
```

OR

```
[normalizeImageSrc] Input length: 0 First 50 chars: 
← No image data received
```

OR

```
[Image Error] Failed to load question image: iVBORw0KGgoAAAA...
← Image failed to render
```

---

### Step 2: Check Network Tab
1. DevTools → **Network** tab
2. Reload test page
3. Find API call: `test-sessions/{id}/` or `questions/`
4. Click on it → **Response** tab
5. Search for `"questionImage"` or `"optionAImage"`

**Expected:**
```json
{
  "id": 123,
  "question": "Which plant family...",
  "questionImage": "iVBORw0KGgoAAAANSUhEUgAA...",  ← Raw base64 (no data: prefix)
  "optionAImage": null
}
```

**If you see:**
```json
{
  "questionImage": null   ← Image not in database!
}
```

---

### Step 3: Check Database
Run the debug script:

```powershell
cd backend
python debug_base64_images.py list
```

**Output should show:**
```
Recent questions with images:
============================================================

ID: 456 | The floral formula ♂♀ K(5) C(5) A5 G(2) represents...
  Image length: 45678 chars

ID: 457 | Another question...
  Image length: 34567 chars
```

**To inspect specific question:**
```powershell
python debug_base64_images.py 456
```

**Expected output:**
```
QUESTION_IMAGE:
  Present: True
  Length: 45678 characters
  First 50 chars: iVBORw0KGgoAAAANSUhEUgAABNQAAAH0CAYAAADQT...
  Last 50 chars: ...ABJRU5ErkJggg==
  Decode test: ✓ Successfully decoded: 34235 bytes
```

---

## 🐛 **Common Issues & Fixes**

### Issue 1: Image Shows Data URI Prefix in Database
**Symptom:**
```
First 50 chars: data:image/png;base64,iVBORw0KGgoAAAA...
⚠ WARNING: Still has data URI prefix! Backend should strip this.
```

**Cause:** Backend normalization failed to strip the prefix

**Fix:** The updated backend code should now strip this. Re-upload the Excel file.

---

### Issue 2: Empty Image Field
**Symptom:**
```json
{
  "questionImage": null
}
```

**Cause 1:** Excel cell was empty
- **Fix:** Ensure Excel cell has base64 data

**Cause 2:** Excel column name mismatch
- **Fix:** Column must be exactly: `question_image`, `option_a_image`, etc.

**Cause 3:** Base64 validation failed (corrupted data)
- **Fix:** Check backend logs for validation errors

---

### Issue 3: Truncated Base64
**Symptom:**
```
Last 50 chars: ...ABJRU5
Decode test: ✗ Decode failed: Incorrect padding
```

**Cause:** Excel cell character limit (32,767 chars)

**Fix Options:**
1. **Use smaller images** (<100KB before encoding)
2. **Compress images** before converting to base64
3. **Use external image hosting** (S3, CDN) and store URLs instead

**Image size calculation:**
```
Original file: 50KB
Base64 size: 50KB × 1.33 = 66.5KB = ~66,500 chars ✓ (fits in Excel)

Original file: 150KB
Base64 size: 150KB × 1.33 = 199.5KB = ~199,500 chars ✗ (Excel limit: 32,767)
```

---

### Issue 4: Browser Can't Decode Base64
**Symptom:** Image broken icon, console shows:
```
[Image Error] Failed to load question image: iVBORw0KGgoAAAA...
```

**Cause 1:** Invalid base64 characters
- Check for special characters, line breaks, or corruption

**Cause 2:** Browser memory limit (very large images)
- Reduce image size

**Fix:** Use the compression utility:
```python
from neet_app.utils.image_utils import compress_base64_image

compressed = compress_base64_image(
    large_base64_string,
    max_width=800,
    quality=85
)
```

---

### Issue 5: MIME Type Detection Failed
**Symptom:** Image shows as download or incorrect format

**Cause:** Base64 doesn't start with recognizable signature

**Common signatures:**
| Format | Base64 Starts With |
|--------|-------------------|
| PNG | `iVBORw0KG` |
| JPEG | `/9j` |
| GIF | `R0lGOD` |

**Fix:** Ensure your image file is actually PNG/JPEG before encoding

---

## ✅ **Testing Checklist**

### 1. Verify Excel Format
```
✓ Column name: question_image (lowercase, with underscore)
✓ Data format: data:image/png;base64,iVBORw0KGgo... OR iVBORw0KGgo...
✓ Cell not empty
✓ Base64 string length < 30,000 chars (safe limit)
```

### 2. Verify Backend Processing
```powershell
# Upload Excel and check backend terminal for logs:
```

**Expected logs:**
```
INFO Processing question_image: Original length = 45678 chars
INFO question_image: Stripped data URI prefix, new length = 45652
INFO question_image: Final base64 length = 45652 chars, prefix = iVBORw0KGgoAAAANSU...
INFO question_image: Base64 validation passed ✓
```

**Bad logs:**
```
WARNING question_image: Invalid data URI format (no comma found)
WARNING question_image: Invalid base64 payload - Incorrect padding
```

### 3. Verify Database Storage
```powershell
python debug_base64_images.py list
```

### 4. Verify API Response
```
DevTools → Network → test-sessions/{id}/ → Response
Check: "questionImage": "iVBORw0KGgoAAAA..." (should have data)
```

### 5. Verify Frontend Rendering
```
DevTools → Console
Look for: [normalizeImageSrc] logs
Check: [Image Success] or [Image Error]
```

---

## 🛠️ **Quick Fixes**

### Fix 1: Re-upload with Smaller Images
```bash
# Reduce image size before encoding
# Target: <100KB original = <140KB base64 = ~140,000 chars
```

### Fix 2: Check Backend Logs
```powershell
# In Django terminal, look for:
INFO question_image: Base64 validation passed ✓
# or
WARNING Invalid base64 image payload
```

### Fix 3: Clear Browser Cache
```
Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### Fix 4: Test with Simple Image
Create a 10×10 PNG test image:
```python
from PIL import Image
import base64
from io import BytesIO

# Create tiny test image
img = Image.new('RGB', (10, 10), color='red')
buffer = BytesIO()
img.save(buffer, format='PNG')
test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
print(f"Test base64 ({len(test_base64)} chars):")
print(f"data:image/png;base64,{test_base64}")
```

Put this in Excel and upload to verify the pipeline works.

---

## 📞 **Need More Help?**

### Enable Debug Mode
Set in `.env`:
```
DEBUG=True
```

Restart Django server and check terminal for detailed logs.

### Get Question Data
```python
# Django shell
from neet_app.models import Question
q = Question.objects.get(id=YOUR_QUESTION_ID)
print("Has image:", bool(q.question_image))
print("Length:", len(q.question_image) if q.question_image else 0)
print("First 100:", q.question_image[:100] if q.question_image else "None")
```

### Test Frontend Manually
Open DevTools console and paste:
```javascript
// Test if browser can render base64
const testImg = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==";
const img = new Image();
img.onload = () => console.log("✓ Test image loaded!");
img.onerror = () => console.error("✗ Test image failed!");
img.src = `data:image/png;base64,${testImg}`;
```

---

## 🎯 **Most Likely Cause**

Based on your screenshot showing a broken image icon:

1. **Most likely:** Base64 string is truncated or corrupted
   - Excel 32K character limit exceeded
   - Copy/paste error

2. **Second most likely:** Backend validation failing
   - Check Django terminal logs during upload
   - Look for "Invalid base64" warnings

3. **Less likely:** Frontend rendering issue
   - Browser console should show errors
   - Check Network tab for API response

**Next Step:** Run `python debug_base64_images.py list` to see if images are actually in the database.

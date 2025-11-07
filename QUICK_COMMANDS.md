# 🚀 Institution Tests - Quick Command Reference

## Essential Commands

### Backend Setup
```powershell
# Navigate to backend
cd f:\ZAIFI\NeetNinja\backend

# Install required package
pip install openpyxl==3.1.2

# Run migrations (already done)
python manage.py migrate

# Create test institution and admin
python test_institution_feature.py

# Start backend server
python manage.py runserver
```

### Frontend Setup
```powershell
# Navigate to frontend
cd f:\ZAIFI\NeetNinja\client

# Install dependencies (if needed)
npm install

# Start development server
npm run dev
```

---

## API Testing Commands

### 1. Login as Institution Admin
```powershell
curl -X POST http://localhost:8000/api/institution-admin/login/ `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"test_admin\", \"password\": \"test_password\"}'
```

**Response**: Copy the `access` token

### 2. Get Available Exam Types
```powershell
curl -X GET http://localhost:8000/api/institution-admin/exam-types/ `
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 3. Upload Excel Test
```powershell
# Create your Excel file first (questions.xlsx)
curl -X POST http://localhost:8000/api/institution-admin/upload/ `
  -H "Authorization: Bearer YOUR_TOKEN_HERE" `
  -F "file=@questions.xlsx" `
  -F "test_name=Sample NEET Test" `
  -F "exam_type=neet" `
  -F "time_limit=180"
```

### 4. List Institution Tests
```powershell
curl -X GET http://localhost:8000/api/institution-admin/tests/ `
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 5. Verify Institution Code (Student)
```powershell
curl -X POST http://localhost:8000/api/institutions/verify-code/ `
  -H "Content-Type: application/json" `
  -d '{\"code\": \"TEST_INST_001\"}'
```

### 6. List Student Tests
```powershell
# Get institution ID from verify-code response
curl -X GET "http://localhost:8000/api/institutions/1/tests/?exam_type=neet" `
  -H "Authorization: Bearer STUDENT_TOKEN_HERE"
```

---

## Quick Testing Flow

### Option A: Manual Testing (Recommended First)
```powershell
# Terminal 1: Backend
cd backend
python manage.py runserver

# Terminal 2: Frontend
cd client
npm run dev

# Terminal 3: Create test data
cd backend
python test_institution_feature.py
```

Then open browser:
1. Go to `http://localhost:5173`
2. Login as student
3. Click "Institution" in navigation
4. Enter code: `TEST_INST_001`
5. Select exam type
6. Start a test

### Option B: API Testing Only
```powershell
# 1. Create test data
python backend/test_institution_feature.py

# 2. Login as admin
curl -X POST http://localhost:8000/api/institution-admin/login/ -H "Content-Type: application/json" -d '{\"username\": \"test_admin\", \"password\": \"test_password\"}'

# 3. Copy token and upload test (after creating Excel)
curl -X POST http://localhost:8000/api/institution-admin/upload/ -H "Authorization: Bearer TOKEN" -F "file=@test.xlsx" -F "test_name=Test" -F "exam_type=neet" -F "time_limit=180"
```

---

## Database Queries (Django Shell)

### Enter Django Shell
```powershell
cd backend
python manage.py shell
```

### Check Institutions
```python
from neet_app.models import Institution, InstitutionAdmin, Question, PlatformTest

# List all institutions
Institution.objects.all()

# Get specific institution
inst = Institution.objects.get(code='TEST_INST_001')
print(f"Name: {inst.name}, Code: {inst.code}")
```

### Check Admins
```python
# List all admins
InstitutionAdmin.objects.all()

# Verify admin can authenticate
admin = InstitutionAdmin.objects.get(username='test_admin')
admin.check_password('test_password')  # Should return True
```

### Check Institution Tests
```python
# List institution tests
PlatformTest.objects.filter(is_institution_test=True)

# Count institution questions
Question.objects.filter(institution__isnull=False).count()
```

### Create New Institution Manually
```python
# Create institution
inst = Institution.objects.create(
    name="My Coaching Center",
    code="COACHING_2024",
    exam_types=["neet", "jee"]
)

# Create admin
admin = InstitutionAdmin.objects.create(
    username="mycoaching_admin",
    institution=inst,
    is_active=True
)
admin.set_password("SecurePass123")
admin.save()

print(f"Created institution: {inst.code}")
```

---

## Troubleshooting Commands

### Check If openpyxl Installed
```powershell
pip show openpyxl
```

### Check Database State
```powershell
python manage.py showmigrations neet_app
# Should show [X] next to 0015_institutionadmin...
```

### View Recent Migrations
```powershell
python manage.py migrate --plan
```

### Check Backend Logs
```powershell
# When running server, watch for errors in terminal
# Or check Django debug toolbar if enabled
```

### Check Frontend Errors
```
# Open browser console (F12)
# Look for network errors or JavaScript errors
```

### Reset Test Data
```powershell
# Django shell
python manage.py shell

# Delete all institution data
from neet_app.models import Institution, InstitutionAdmin, Question, PlatformTest
Question.objects.filter(institution__isnull=False).delete()
PlatformTest.objects.filter(is_institution_test=True).delete()
InstitutionAdmin.objects.all().delete()
Institution.objects.all().delete()

# Re-run test script
exit()
python test_institution_feature.py
```

---

## File Locations

### Backend Files
```
backend/
├── neet_app/
│   ├── models.py                          # Database models
│   ├── institution_auth.py                # JWT authentication
│   ├── services/institution_upload.py     # Excel parser
│   ├── views/institution_admin_views.py   # Admin endpoints
│   └── views/institution_student_views.py # Student endpoints
├── test_institution_feature.py            # Test script
└── sample_institution_test_template.md    # Excel format guide
```

### Frontend Files
```
client/src/
├── components/InstitutionTester/
│   ├── index.tsx                          # Main component
│   ├── InstitutionCodeModal.tsx          # Code entry
│   └── InstitutionTestsList.tsx          # Test listing
├── pages/institution-tester.tsx           # Page wrapper
└── App.tsx                                # Routing
```

### Documentation
```
INSTITUTION_TESTS_IMPLEMENTATION.md        # Full implementation doc
INSTITUTION_TESTS_COMPLETE.md              # Quick summary
backend/sample_institution_test_template.md # Excel guide
```

---

## Excel File Creation

### Quick Excel Template
Open Excel and create:

**Row 1 (Headers):**
| question_text | option_a | option_b | option_c | option_d | correct_answer | explanation |

**Row 2 (Example):**
| What is 2+2? | 2 | 4 | 6 | 8 | B | 2+2 equals 4 |

**Save as**: `questions.xlsx`

---

## Environment Variables

### Backend (.env)
```
FEATURE_INSTITUTION_TESTS=True
```

---

## Port Numbers

- **Backend**: `http://localhost:8000`
- **Frontend**: `http://localhost:5173` (Vite default)

---

## Status Check

### Verify Everything Works
```powershell
# 1. Backend dependencies
pip show openpyxl django djangorestframework

# 2. Migrations
python manage.py showmigrations neet_app | Select-String "0015"

# 3. Test data
python manage.py shell -c "from neet_app.models import Institution; print(Institution.objects.count())"

# 4. Start servers
# Terminal 1: python manage.py runserver
# Terminal 2: npm run dev (from client folder)
```

---

## Quick Test (30 seconds)

```powershell
# 1. Create data
python backend/test_institution_feature.py

# 2. Test API
curl http://localhost:8000/api/institutions/verify-code/ -X POST -H "Content-Type: application/json" -d '{\"code\": \"TEST_INST_001\"}'

# Should return institution details
```

---

## 🎯 Next Steps

1. ✅ Run `backend/test_institution_feature.py`
2. ✅ Create sample Excel file
3. ✅ Test upload via API
4. ✅ Test frontend flow
5. ✅ Create real institution data
6. ✅ Deploy to staging/production

**Status**: Ready to test! 🚀

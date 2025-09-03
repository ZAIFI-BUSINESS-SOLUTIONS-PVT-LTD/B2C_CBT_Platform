#!/usr/bin/env python
import os
import sys
import django
import json
from pprint import pprint

# Ensure backend directory is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile
from neet_app.views.dashboard_views import platform_test_analytics
from django.http import HttpRequest

TARGET_STUDENT_ID = 'STU250309CRJ225'

print(f"Looking up student {TARGET_STUDENT_ID}...")
student = StudentProfile.objects.filter(student_id=TARGET_STUDENT_ID).first()
if not student:
    print('Student not found in DB. Exiting.')
    sys.exit(2)

print(f"Found student: {student.student_id} - {student.full_name}\n")

# Create request
request = HttpRequest()
request.method = 'GET'
request.user = student

# Call endpoint without test_id first
print('Calling platform_test_analytics without test_id...')
response = platform_test_analytics(request)
print(f'Status: {response.status_code}')
try:
    data = response.data
    print('Response payload (overview):')
    pprint(data)
except Exception as e:
    print('Failed to read response data:', e)

# If there are available tests, call with first test id
available = []
try:
    available = response.data.get('availableTests') or []
except Exception:
    available = []

if available:
    test_id = available[0].get('id')
    print(f"\nCalling platform_test_analytics with test_id={test_id}...")
    # attach GET params
    request.GET = {'test_id': str(test_id)}
    response2 = platform_test_analytics(request)
    print(f'Status: {response2.status_code}')
    try:
        data2 = response2.data
        print('Response payload (selectedTestMetrics):')
        pprint(data2)
    except Exception as e:
        print('Failed to read response data for selected test:', e)
else:
    print('\nNo available platform tests for this student.')

print('\nDone.')

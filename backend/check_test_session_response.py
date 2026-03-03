"""
Check what the test session API actually returns
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from django.test import RequestFactory
from neet_app.models import StudentProfile, TestSession
from neet_app.views.test_session_views import get_test_session

# Get student
student = StudentProfile.objects.get(student_id='MOB260222IVCJOV')

# Get latest test session
session = TestSession.objects.filter(student_id=student.student_id).order_by('-id').first()

print(f"Latest session ID: {session.id}")

# Create mock request
factory = RequestFactory()
request = factory.get(f'/api/test-sessions/{session.id}/')
request.user = student

# Call the view
from rest_framework.request import Request
from rest_framework.test import force_authenticate

drf_request = Request(request)
force_authenticate(drf_request, user=student)

response = get_test_session(drf_request, session.id)

print(f"\nStatus: {response.status_code}")
print(f"\nResponse keys: {list(response.data.keys())}")
print(f"\nSession keys: {list(response.data.get('session', {}).keys())}")
print(f"\nFull response data (formatted):")
print(json.dumps(response.data, indent=2, default=str))

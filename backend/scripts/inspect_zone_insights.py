# Helper script to inspect zone insights using Django shell input redirection
# Run with: python manage.py shell < scripts/inspect_zone_insights.py

from django.test.client import RequestFactory
from django.contrib.auth import get_user_model
from neet_app.views.zone_insights_views import get_student_tests, get_test_zone_insights
import pprint

rf = RequestFactory()
User = get_user_model()
user = User.objects.first()
print('User:', user)

req = rf.get('/api/zone-insights/tests/')
req.user = user
res = get_student_tests(req)
print('TEST LIST STATUS:', getattr(res, 'status_code', 'N/A'))

data = res.data if hasattr(res, 'data') else {}
tests = data.get('tests', []) if isinstance(data, dict) else []
print('TOTAL TESTS:', len(tests))

if tests:
    first = tests[0]
    test_id = first.get('id')
    print('Calling get_test_zone_insights for id', test_id)
    req2 = rf.get(f'/api/zone-insights/test/{test_id}/')
    req2.user = user
    res2 = get_test_zone_insights(req2, test_id)
    print('STATUS', getattr(res2, 'status_code', 'N/A'))
    pprint.pprint(res2.data)
else:
    print('No tests to inspect')

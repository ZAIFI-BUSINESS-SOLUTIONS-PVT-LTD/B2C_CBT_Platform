"""
Test what the API endpoint returns
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import TestSession, TestAnswer
from django.db.models import Exists, OuterRef

print("=" * 60)
print("SIMULATING API RESPONSE")
print("=" * 60)

# Simulate what get_student_tests returns
tests = TestSession.objects.filter(
    is_completed=True
).annotate(
    has_answers=Exists(
        TestAnswer.objects.filter(session_id=OuterRef('id'))
    )
).filter(has_answers=True).order_by('-end_time')

print(f"\nFound {tests.count()} tests with answers\n")

# Format test data like the view does
tests_data = []
for test in tests[:3]:
    # Calculate marks
    total_marks = (test.correct_answers * 4) - (test.incorrect_answers * 1)
    max_marks = test.total_questions * 4
    
    # Determine test name
    if test.test_type == 'platform' and test.platform_test:
        test_name = test.platform_test.test_name
    else:
        test_name = f"Practice Test #{test.id}"
    
    test_dict = {
        'id': test.id,
        'test_type': test.test_type,
        'test_name': test_name,
        'start_time': test.start_time.isoformat() if test.start_time else None,
        'end_time': test.end_time.isoformat() if test.end_time else None,
        'total_questions': test.total_questions,
        'correct_answers': test.correct_answers,
        'incorrect_answers': test.incorrect_answers,
        'unanswered': test.unanswered,
        'total_marks': total_marks,
        'max_marks': max_marks,
        'physics_score': test.physics_score,
        'chemistry_score': test.chemistry_score,
        'botany_score': test.botany_score,
        'zoology_score': test.zoology_score,
        'math_score': test.math_score
    }
    
    tests_data.append(test_dict)
    
    print(f"Test {test.id}:")
    print(f"  test_name: {test_dict['test_name']}")
    print(f"  start_time: {test_dict['start_time']}")
    print(f"  end_time: {test_dict['end_time']}")
    print(f"  total_marks: {test_dict['total_marks']}")
    print(f"  max_marks: {test_dict['max_marks']}")
    print(f"  total_questions: {test_dict['total_questions']}")
    print(f"  correct_answers: {test_dict['correct_answers']}")
    print(f"  incorrect_answers: {test_dict['incorrect_answers']}")
    print()

print("=" * 60)
print("API Response would be:")
print({
    'status': 'success',
    'tests': tests_data,
    'total_tests': len(tests_data)
})

#!/usr/bin/env python
"""
Test script to check platform test analytics endpoint
"""
import os
import sys
import django
import requests
import json

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import PlatformTest, TestSession, StudentProfile, TestAnswer
from django.db.models import Sum, Count

def test_platform_test_analytics():
    """Test the platform test analytics endpoint"""
    
    print("=== Platform Test Analytics Test ===\n")
    
    # 1. Check platform tests in database
    print("1. Checking platform tests in database:")
    platform_tests = PlatformTest.objects.all()
    print(f"   Total platform tests: {platform_tests.count()}")
    
    for test in platform_tests:
        print(f"   - ID: {test.id}, Name: {test.test_name}, Active: {test.is_active}")
    print()
    
    # 2. Check students in database
    print("2. Checking students in database:")
    students = StudentProfile.objects.all()
    print(f"   Total students: {students.count()}")
    
    if students.exists():
        student = students.first()
        print(f"   First student: {student.student_id} - {student.full_name}")
    print()
    
    # 3. Check test sessions
    print("3. Checking test sessions:")
    sessions = TestSession.objects.filter(test_type='platform')
    print(f"   Total platform test sessions: {sessions.count()}")
    
    for session in sessions[:3]:
        print(f"   - Session {session.id}: Student {session.student_id}, Test: {session.platform_test.test_name if session.platform_test else 'None'}, Completed: {session.is_completed}")
    print()
    
    # 4. Test the API endpoint manually
    print("4. Testing API endpoint logic:")
    
    try:
        from neet_app.views.dashboard_views import platform_test_analytics
        from django.http import HttpRequest
        from django.contrib.auth.models import AnonymousUser
        
        # Create a mock request
        request = HttpRequest()
        request.method = 'GET'
        
        # Simulate an authenticated user (using first student)
        if students.exists():
            student = students.first()
            request.user = student
            
            print(f"   Testing with student: {student.student_id}")
            
            # Test without test_id parameter
            print("   - Testing endpoint without test_id...")
            response = platform_test_analytics(request)
            data = response.data

            print(f"   - Response status: {response.status_code}")
            print(f"   - Available tests count: {len(data.get('availableTests', []))}")
            print(f"   - Available tests: {[t['testName'] for t in data.get('availableTests', [])]}")
            print(f"   - Selected test metrics: {data.get('selectedTestMetrics')}")
            print()

            # Test with test_id parameter
            if platform_tests.exists():
                test_id = platform_tests.first().id
                print(f"   - Testing endpoint with test_id={test_id}...")
                request.GET = {'test_id': str(test_id)}
                response = platform_test_analytics(request)
                data = response.data

                print(f"   - Response status: {response.status_code}")
                print(f"   - Selected test metrics (from endpoint): {json.dumps(data.get('selectedTestMetrics'), indent=2)}")

                # -------------------------
                # Reproduce the backend calculation here and print intermediate values
                # -------------------------
                print('\n   Backend calculation reproduction:')
                selected_test = PlatformTest.objects.get(id=test_id)
                all_sessions = TestSession.objects.filter(
                    test_type='platform', platform_test=selected_test, is_completed=True
                ).order_by('-start_time')

                print(f"   - Total completed sessions for test {test_id}: {all_sessions.count()}")

                # Build per-student best percentage mapping using TestAnswer records
                student_best = {}
                most_recent_for_current = None
                for s in all_sessions:
                    answers_qs = TestAnswer.objects.filter(session=s)
                    total_answers = answers_qs.count()
                    if total_answers > 0:
                        correct_count = answers_qs.filter(is_correct=True).count()
                        percent = (correct_count / total_answers) * 100
                    else:
                        percent = (s.correct_answers / s.total_questions * 100) if s.total_questions else 0

                    prev = student_best.get(s.student_id)
                    if prev is None or percent > prev:
                        student_best[s.student_id] = percent

                    if s.student_id == student.student_id and most_recent_for_current is None:
                        most_recent_for_current = s

                print(f"   - Distinct students who took test: {len(student_best)}")
                print(f"   - Per-student best percentages: \n     {json.dumps(student_best, indent=4)}")

                if most_recent_for_current:
                    cur_percent = student_best.get(student.student_id)
                    print(f"   - Current student's most recent session id: {most_recent_for_current.id}")
                    print(f"   - Current student's percent (most recent/best): {cur_percent}")

                    # Rank calculation (descending)
                    sorted_students = sorted(student_best.items(), key=lambda kv: kv[1], reverse=True)
                    print(f"   - Sorted (student_id, percent) desc: \n     {json.dumps(sorted_students, indent=4)}")
                    rank = next((i for i, (sid, pct) in enumerate(sorted_students, start=1) if sid == student.student_id), None)
                    num_below = sum(1 for pct in student_best.values() if pct < cur_percent)
                    num_equal = sum(1 for pct in student_best.values() if pct == cur_percent)
                    percentile_calc = ((num_below + (num_equal / 2)) / len(student_best)) * 100 if len(student_best) > 0 else 0

                    print(f"   - Computed rank: {rank}")
                    print(f"   - num_below: {num_below}, num_equal: {num_equal}")
                    print(f"   - Computed percentile (midpoint method): {percentile_calc:.2f}")

                    # Avg time per question
                    if most_recent_for_current.total_time_taken and most_recent_for_current.total_questions:
                        avg_time = most_recent_for_current.total_time_taken / most_recent_for_current.total_questions
                        print(f"   - Avg time per question (from session.total_time_taken): {avg_time:.2f} sec")
                    else:
                        ans_agg = TestAnswer.objects.filter(session=most_recent_for_current).aggregate(total_time=Sum('time_taken'), cnt=Count('id'))
                        total_time = ans_agg.get('total_time') or 0
                        cnt = ans_agg.get('cnt') or 0
                        avg_time = (total_time / cnt) if cnt > 0 else 0
                        print(f"   - Avg time per question (from TestAnswer aggregation): {avg_time:.2f} sec (total_time={total_time}, count={cnt})")
                else:
                    print('   - Student has not taken this selected platform test yet.')
                    # Print leaderboard if present
                    lb = data.get('selectedTestMetrics', {}).get('leaderboard')
                    if lb:
                        print('\n   Leaderboard (top 3):')
                        for entry in lb:
                            print(f"     Rank {entry['rank']}: {entry['studentName']} ({entry['studentId']}) - Accuracy: {entry['accuracy']}%, Time(s): {entry['timeTakenSec']}")
            
        else:
            print("   No students found to test with")
            
    except Exception as e:
        print(f"   Error testing endpoint: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_platform_test_analytics()

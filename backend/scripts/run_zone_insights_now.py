#!/usr/bin/env python
"""
Run zone insights computation for the most recent completed TestSession
against the current configured database (no test DB created).

Run from the `backend` folder:

    python scripts/run_zone_insights_now.py

"""
import os
import sys
from pathlib import Path

# Ensure backend package is importable
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
import django
django.setup()

from neet_app.models import TestSession, TestSubjectZoneInsight, StudentProfile
from neet_app.services.zone_insights_service import compute_and_store_zone_insights


def main():
    session = TestSession.objects.filter(is_completed=True).order_by('-end_time').first()
    if not session:
        print('No completed TestSession found in the database. Aborting.')
        return 1

    print(f'Found session id={session.id}, student_id={session.student_id}, test_type={session.test_type}')

    # Ensure student profile exists
    student = StudentProfile.objects.filter(student_id=session.student_id).first()
    if not student:
        print(f'No StudentProfile for student_id={session.student_id}. Aborting.')
        return 1

    print('Computing zone insights...')
    try:
        compute_and_store_zone_insights(session.id)
    except Exception as e:
        print('Error while computing zone insights:', e)
        raise

    insight = TestSubjectZoneInsight.objects.filter(test_session=session, student=student).first()
    if not insight:
        print('No TestSubjectZoneInsight created.')
        return 1

    print('\n=== Stored Insight Summary ===')
    print('session:', session.id)
    print('student:', session.student_id)
    print('mark:', insight.mark)
    print('total_mark:', insight.total_mark)
    print('accuracy:', insight.accuracy)
    print('time_spend:', insight.time_spend)
    print('subject_data:', insight.subject_data)
    print('g_phrase:', insight.g_phrase)
    print('===============================')
    return 0


if __name__ == '__main__':
    sys.exit(main())

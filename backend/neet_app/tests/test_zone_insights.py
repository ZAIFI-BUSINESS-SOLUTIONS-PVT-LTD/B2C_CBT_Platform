from django.test import TestCase
from django.utils import timezone

from neet_app.models import (
    StudentProfile, TestSession, TestSubjectZoneInsight
)
from neet_app.services.zone_insights_service import compute_and_store_zone_insights


class ZoneInsightsServiceTest(TestCase):
    def test_compute_and_store_zone_insights_on_recent_session(self):
        # Use the most recent completed TestSession from the DB for this test run.
        session = TestSession.objects.filter(is_completed=True).order_by('-end_time').first()
        if not session:
            self.skipTest('No completed TestSession found in DB. Populate test sessions before running this test.')

        # Ensure student profile exists for the session.student_id
        student = StudentProfile.objects.filter(student_id=session.student_id).first()
        if not student:
            self.skipTest(f'No StudentProfile found for student_id={session.student_id} (session {session.id})')

        # Run the service for the chosen session
        compute_and_store_zone_insights(session.id)

        # Fetch stored insight
        insight = TestSubjectZoneInsight.objects.filter(test_session=session, student=student).first()
        self.assertIsNotNone(insight, f'Expected TestSubjectZoneInsight for session {session.id}')

        # Validate required fields exist and have expected types
        self.assertIsNotNone(insight.total_mark)
        self.assertIsNotNone(insight.mark)
        self.assertIsNotNone(insight.accuracy)
        self.assertIsInstance(insight.time_spend or {}, dict)
        self.assertIsInstance(insight.subject_data or [], list)
        # g_phrase may be None or a string depending on history; ensure no error
        self.assertTrue((insight.g_phrase is None) or isinstance(insight.g_phrase, str))

        # Print values to help manual inspection when running tests
        print('session:', session.id)
        print('student:', session.student_id)
        print('mark:', insight.mark)
        print('total_mark:', insight.total_mark)
        print('accuracy:', insight.accuracy)
        print('time_spend:', insight.time_spend)
        print('subject_data:', insight.subject_data)
        print('g_phrase:', insight.g_phrase)


if __name__ == '__main__':
    import pytest

    pytest.main([__file__])

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import StudentProfile, TestSession
from ...notifications import dispatch_inactivity_reminder


class Command(BaseCommand):
    help = 'Send inactivity reminder emails to students who have not taken a test in more than 5 days'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=5, help='Days of inactivity threshold')
        parser.add_argument('--limit', type=int, default=0, help='Optional limit number of emails to send (0 means no limit)')

    def handle(self, *args, **options):
        days = options.get('days', 5)
        limit = options.get('limit', 0)
        now = timezone.now()
        cutoff = now - timedelta(days=days)

        students = StudentProfile.objects.filter(is_active=True)

        sent_count = 0
        skipped_no_email = 0

        for student in students:
            if limit and sent_count >= limit:
                break

            # Get latest completed test session for this student
            last_session = TestSession.objects.filter(student_id=student.student_id, is_completed=True).order_by('-end_time').first()

            if last_session and last_session.end_time:
                if last_session.end_time >= cutoff:
                    # recent enough, skip
                    continue
                last_test_date = last_session.end_time
            else:
                # No completed session found — treat as inactive
                last_test_date = None

            # Skip if no email
            if not getattr(student, 'email', None):
                skipped_no_email += 1
                continue

            try:
                dispatch_inactivity_reminder(student, last_test_date=last_test_date)
                sent_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to send reminder to {student.student_id}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} inactivity reminders (skipped {skipped_no_email} students without email)'))

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import PasswordReset


class Command(BaseCommand):
    help = 'Clean up expired or old used password reset records'

    def handle(self, *args, **options):
        now = timezone.now()
        # Delete expired tokens older than 30 minutes
        expired = PasswordReset.objects.filter(expires_at__lt=now)
        count_expired = expired.count()
        expired.delete()

        # Optionally delete used tokens older than 7 days
        cutoff = now - timedelta(days=7)
        old_used = PasswordReset.objects.filter(used=True, created_at__lt=cutoff)
        count_old_used = old_used.count()
        old_used.delete()

        self.stdout.write(self.style.SUCCESS(f'Deleted {count_expired} expired tokens and {count_old_used} old used tokens'))

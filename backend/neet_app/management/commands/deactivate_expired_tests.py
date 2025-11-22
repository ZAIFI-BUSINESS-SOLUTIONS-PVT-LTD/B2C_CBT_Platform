from django.core.management.base import BaseCommand
from django.utils import timezone

from neet_app.models import PlatformTest


class Command(BaseCommand):
    help = "Deactivate PlatformTests whose expires_at has passed"

    def handle(self, *args, **options):
        now = timezone.now()
        qs = PlatformTest.objects.filter(expires_at__lte=now, is_active=True)
        count = qs.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {count} expired tests"))

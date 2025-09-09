from __future__ import annotations
import os
from celery import Celery

# Use the Django settings module for this project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')

app = Celery('neet_backend')

# Load configuration from Django settings, using CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    return f'Request: {self.request!r}'

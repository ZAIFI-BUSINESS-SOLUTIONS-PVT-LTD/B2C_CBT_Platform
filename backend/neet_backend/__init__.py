"""neet_backend package init.

Ensure Celery app is imported when Django starts so tasks can be discovered by workers.
"""
from .celery import app as celery_app  # noqa: F401

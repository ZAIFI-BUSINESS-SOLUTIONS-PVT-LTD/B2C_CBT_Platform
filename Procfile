web: gunicorn neet_backend.wsgi:application --chdir backend --bind 0.0.0.0:8000 --workers 3
worker: celery -A neet_backend worker --loglevel=INFO --concurrency=2

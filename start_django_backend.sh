#!/bin/bash

# Start Django backend for NEET Practice Platform
echo "Starting Django backend on port 8001..."

cd backend && python manage.py runserver 0.0.0.0:8001 > /tmp/django_backend.log 2>&1 &
DJANGO_PID=$!

echo "Django backend started with PID: $DJANGO_PID"
echo "Django backend is running on http://localhost:8001"
echo "API available at http://localhost:8001/api/"

# Keep the script running
wait $DJANGO_PID
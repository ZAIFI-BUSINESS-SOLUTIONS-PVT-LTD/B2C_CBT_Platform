#!/bin/bash
set -e
source /var/app/venv/*/bin/activate
cd /var/app/current
python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput

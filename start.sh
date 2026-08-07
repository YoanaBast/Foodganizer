#!/bin/sh
set -e
python manage.py migrate
python manage.py collectstatic --noinput
exec gunicorn meals_manager.wsgi:application --bind 0.0.0.0:$PORT --workers 1

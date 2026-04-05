import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_manager.settings')

app = Celery('meals_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
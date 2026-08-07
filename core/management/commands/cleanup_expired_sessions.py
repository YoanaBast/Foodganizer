from django.core.management.base import BaseCommand
from core.tasks import cleanup_expired_sessions

class Command(BaseCommand):
    def handle(self, *args, **options):
        cleanup_expired_sessions()  # call the function body directly, not .delay()

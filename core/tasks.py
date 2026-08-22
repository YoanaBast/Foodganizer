# CURRENTLY UNUSED AS THE WORKERS ON RENDER ARE NOT FREE, GOOD ON AWS DELPOYMENT


from celery import shared_task

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone

import logging
from users.emails import send_welcome_email


logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email_task(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'send_welcome_email_task: user {user_id} not found')
        return
    send_welcome_email(user)


@shared_task
def cleanup_expired_sessions():
    """
    Scheduled nightly at 2am UTC via Celery Beat.
    Deletes expired sessions from the database.
    """

    deleted, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
    logger.info(f'cleanup_expired_sessions: deleted {deleted} expired sessions')
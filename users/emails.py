from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user):
    send_mail(
        subject='Welcome to Foodganizer!',
        message=(
            f'Hi {user.first_name or user.username},\n\n'
            "Welcome to Foodganizer! We're glad you're here.\n\n"
            'Start organizing your meals and enjoy the experience.\n\n'
            '— The Foodganizer Team'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
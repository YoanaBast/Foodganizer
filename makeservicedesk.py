import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_manager.settings')
django.setup()

import sys
from django.contrib.auth.models import User, Group


def make_service_desk(username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"User '{username}' not found.")
        sys.exit(1)

    group, _ = Group.objects.get_or_create(name='Service Desk')
    user.groups.add(group)
    user.is_staff = True
    user.save()
    print(f"'{username}' is now a Service Desk agent with admin access.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python makeservicedesk.py <username>")
        sys.exit(1)

    make_service_desk(sys.argv[1])
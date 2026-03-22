import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_manager.settings')
django.setup()

import sys
from django.contrib.auth.models import User, Group


def make_moderator(username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"User '{username}' not found.")
        sys.exit(1)

    group, _ = Group.objects.get_or_create(name='Moderator')
    user.groups.add(group)
    user.is_staff = True
    user.save()

    print(f"'{username}' is now a Moderator.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python makemoderator.py <username>")
        sys.exit(1)

    make_moderator(sys.argv[1])
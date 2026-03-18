from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
            print(f"Found by email: {user}")
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=username)
                print(f"Found by username: {user}")
            except User.DoesNotExist:
                print("User not found")
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        print("Password check failed")
        return None
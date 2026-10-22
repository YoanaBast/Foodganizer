from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models

from simple_history.models import HistoricalRecords
from simple_history import register

# Create your models here.

UserModel = get_user_model()
register(UserModel, app="users")

class Profile(models.Model):

    user = models.OneToOneField(UserModel, primary_key=True, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.user.username

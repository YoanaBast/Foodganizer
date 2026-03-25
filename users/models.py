from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models

from simple_history.models import HistoricalRecords
from simple_history import register

# Create your models here.

UserModel = get_user_model()
register(UserModel)

class Profile(models.Model):

    user = models.OneToOneField(UserModel, primary_key=True, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.user.username

# class AbstractUser(AbstractBaseUser, PermissionsMixin):
#     username = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
#     first_name = models.CharField(_("first name"), max_length=150, blank=True)
#     last_name = models.CharField(_("last name"), max_length=150, blank=True)
#     email = models.EmailField(_("email address"), blank=True)
#     is_staff = models.BooleanField(
#         _("staff status"),
#         default=False,
#         help_text=_("Designates whether the user can log into this admin site."),
#     )
#     is_active = models.BooleanField(
#         _("active"),
#         default=True,
#         help_text=_(
#             "Designates whether this user should be treated as active. "
#             "Unselect this instead of deleting accounts."
#         ),
#     )
#     date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
#     objects = UserManager()
#     EMAIL_FIELD = "email"
#     USERNAME_FIELD = "username"
#     REQUIRED_FIELDS = ["email"]

#     def clean(self):
#         super().clean()
#         self.email = self.__class__.objects.normalize_email(self.email)
#
#     def get_full_name(self):
#         """
#         Return the first_name plus the last_name, with a space in between.
#         """

#     def get_short_name(self):
#         return self.first_name
#
#     def email_user(self, subject, message, from_email=None, **kwargs):
#         """Send an email to this user."""
#         send_mail(subject, message, from_email, [self.email], **kwargs)
#

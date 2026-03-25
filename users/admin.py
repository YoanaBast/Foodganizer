from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from simple_history.admin import SimpleHistoryAdmin
from .models import Profile


class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'get_groups')

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()]) or "-"
    get_groups.short_description = 'Groups'


@admin.register(Profile)
class ProfileAdmin(SimpleHistoryAdmin):
    list_display = ('user', 'bio', 'profile_picture')


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
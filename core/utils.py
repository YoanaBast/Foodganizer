def is_moderator(user):
    return user.groups.filter(name='Moderator').exists()
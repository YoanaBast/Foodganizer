from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from .models import Profile

# delete old file when updating
@receiver(pre_save, sender=Profile)
def delete_old_profile_picture(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return

    if old.profile_picture and old.profile_picture != instance.profile_picture:
        # print(f"Deleting old picture: {old.profile_picture.path}")
        old.profile_picture.delete(save=False)

# delete file when object deleted
@receiver(post_delete, sender=Profile)
def delete_profile_picture_on_delete(sender, instance, **kwargs):
    if instance.profile_picture:
        instance.profile_picture.delete(save=False)
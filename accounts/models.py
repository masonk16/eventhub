from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models

MODERATOR_GROUP = "Moderators"


class User(AbstractUser):
    class Type(models.TextChoices):
        ATTENDEE = "attendee", "Attendee"
        PROMOTER = "promoter", "Promoter"
        MODERATOR = "moderator", "Moderator"

    user_type = models.CharField(max_length=12, choices=Type.choices, default=Type.ATTENDEE)

    @property
    def is_promoter(self):
        return self.user_type == self.Type.PROMOTER or self.is_superuser

    @property
    def is_moderator(self):
        return self.user_type == self.Type.MODERATOR or self.is_superuser

    def save(self, *args, **kwargs):
        # Admin access follows the user type, so demoting a moderator removes it.
        self.is_staff = self.user_type == self.Type.MODERATOR or self.is_superuser
        super().save(*args, **kwargs)
        if self.user_type == self.Type.MODERATOR:
            group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
            self.groups.add(group)
        else:
            group = Group.objects.filter(name=MODERATOR_GROUP).first()
            if group:
                self.groups.remove(group)


class PromoterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="promoter_profile")
    organization_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.organization_name

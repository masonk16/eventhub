from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from accounts.models import MODERATOR_GROUP, User


class Command(BaseCommand):
    help = "Create the Moderators group, give it review permissions, and sync its members."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
        group.permissions.set(Permission.objects.filter(
            content_type__app_label="events",
            codename__in=["view_event", "change_event", "view_verificationrequest", "change_verificationrequest"],
        ))
        group.user_set.set(User.objects.filter(user_type=User.Type.MODERATOR))
        self.stdout.write(self.style.SUCCESS("Moderators group ready."))

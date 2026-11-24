from django.core.management.base import BaseCommand
from django.utils.text import slugify

from events.models import Category

NAMES = ["Music", "Arts & Culture", "Food & Drink", "Sports & Fitness", "Business & Networking",
         "Tech", "Community", "Education", "Faith", "Family & Kids", "Nightlife", "Festivals", "Other"]


class Command(BaseCommand):
    help = "Create a starter set of event categories."

    def handle(self, *args, **options):
        for name in NAMES:
            Category.objects.get_or_create(slug=slugify(name), defaults={"name": name})
        self.stdout.write(self.style.SUCCESS(f"{len(NAMES)} categories ready."))

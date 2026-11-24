import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def new_token():
    return secrets.token_hex(8)


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    class Verification(models.TextChoices):
        UNVERIFIED = "unverified", "Not verified"
        PENDING = "pending", "Review pending"
        VERIFIED = "verified", "Verified organizer"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, editable=False)
    description = models.TextField()
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    organizer_name = models.CharField(max_length=150, help_text="Who is putting this event on?")

    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)

    venue_name = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_online = models.BooleanField(default=False)
    online_url = models.URLField(blank=True, help_text="Link to join, if the event is online.")

    is_free = models.BooleanField(default=False)
    price_info = models.CharField(max_length=200, blank=True, help_text='e.g. "From $10", "$5 / $15 VIP"')
    ticket_url = models.URLField(blank=True, help_text="Where people can get tickets.")
    ticket_info = models.TextField(blank=True, help_text="Other ways to get tickets (outlets, phone, at the door).")

    official_website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    image_url = models.URLField(blank=True, help_text="Link to a poster or banner image.")

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED)

    verification_status = models.CharField(max_length=12, choices=Verification.choices, default=Verification.UNVERIFIED)
    verification_method = models.CharField(max_length=12, blank=True)
    verification_token = models.CharField(max_length=32, default=new_token, editable=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [models.Index(fields=["status", "start_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "event"
            slug, n = base, 2
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.slug])

    @property
    def is_verified(self):
        return self.verification_status == self.Verification.VERIFIED

    @property
    def token_snippet(self):
        return f"eventhub-verify={self.verification_token}"

    @property
    def is_upcoming(self):
        now = timezone.now()
        return self.start_at >= now or (self.end_at is not None and self.end_at >= now)

    def mark_verified(self, method):
        self.verification_status = self.Verification.VERIFIED
        self.verification_method = method
        self.verified_at = timezone.now()
        self.save(update_fields=["verification_status", "verification_method", "verified_at", "updated_at"])

    def reset_verification(self):
        self.verification_status = self.Verification.UNVERIFIED
        self.verification_method = ""
        self.verified_at = None
        self.verification_token = new_token()


class VerificationRequest(models.Model):
    """A manual ownership claim that a staff member reviews."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="verification_requests")
    evidence = models.TextField(help_text="How can we confirm you run this event?")
    proof_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewer_note = models.TextField(blank=True, help_text="Shown to the organizer if rejected.")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event} ({self.get_status_display()})"

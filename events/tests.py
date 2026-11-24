from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import verification
from .forms import EventForm
from .models import Event

PW = "Str0ng-pass!9"


def make_user(name, **kw):
    return get_user_model().objects.create_user(name, password=PW, user_type=kw.pop("user_type", "promoter"), **kw)


def make_event(owner, **kw):
    defaults = dict(title="Jazz Night", description="Live.", organizer_name="Harare Jazz",
                    start_at=timezone.now() + timedelta(days=3), city="Harare", is_free=True,
                    official_website="https://hararejazz.example/", ticket_url="https://hararejazz.example/tickets")
    defaults.update(kw)
    return Event.objects.create(owner=owner, **defaults)


class VerificationTests(TestCase):
    def setUp(self):
        self.event = make_event(make_user("promoter"))

    def test_website_proof_accepts_token_on_own_domain(self):
        page = f"<html><!-- {self.event.token_snippet} --></html>"
        with mock.patch.object(verification, "safe_fetch", return_value=page):
            ok, _ = verification.check_website_proof(self.event, "https://hararejazz.example/about")
        self.assertTrue(ok)

    def test_website_proof_rejects_other_domain(self):
        ok, _ = verification.check_website_proof(self.event, "https://evil.example/page")
        self.assertFalse(ok)

    def test_website_proof_rejects_missing_token(self):
        with mock.patch.object(verification, "safe_fetch", return_value="<html></html>"):
            ok, _ = verification.check_website_proof(self.event, "https://hararejazz.example/")
        self.assertFalse(ok)

    def test_email_must_match_domain(self):
        self.assertTrue(verification.check_email_eligibility(self.event, "info@hararejazz.example")[0])
        self.assertFalse(verification.check_email_eligibility(self.event, "me@gmail.com")[0])

    def test_changing_ticket_link_resets_verification(self):
        self.event.mark_verified("website")
        data = {"title": "Jazz Night", "description": "Live.", "organizer_name": "Harare Jazz",
                "start_at": (timezone.localtime() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
                "city": "Harare", "is_free": "on", "status": "published",
                "official_website": "https://hararejazz.example/", "ticket_url": "https://other.example/t"}
        form = EventForm(data, instance=self.event)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.save().is_verified)


class AccessTests(TestCase):
    def setUp(self):
        self.a, self.b = make_user("a"), make_user("b")
        self.event = make_event(self.a)

    def test_other_promoter_cannot_edit(self):
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(reverse("events:edit", args=[self.event.slug])).status_code, 404)

    def test_draft_hidden_from_public(self):
        self.event.status = Event.Status.DRAFT
        self.event.save()
        self.assertEqual(self.client.get(self.event.get_absolute_url()).status_code, 404)

    def test_list_shows_published(self):
        self.assertContains(self.client.get(reverse("events:list")), "Jazz Night")

    def test_owner_can_open_verify_page(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.get(reverse("events:verify", args=[self.event.slug])).status_code, 200)

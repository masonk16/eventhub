from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PromoterProfile

User = get_user_model()
PW = "Str0ng-pass!9"


class SignupTests(TestCase):
    def signup(self, **extra):
        data = {"username": "sam", "email": "sam@example.com", "password1": PW, "password2": PW,
                "user_type": "attendee", **extra}
        return self.client.post(reverse("accounts:signup"), data)

    def test_attendee_signup(self):
        self.signup()
        self.assertEqual(User.objects.get(username="sam").user_type, "attendee")

    def test_promoter_needs_organization(self):
        r = self.signup(user_type="promoter")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="sam").exists())

    def test_promoter_signup_creates_profile(self):
        self.signup(user_type="promoter", organization_name="Harare Jazz")
        self.assertEqual(PromoterProfile.objects.get(user__username="sam").organization_name, "Harare Jazz")

    def test_cannot_sign_up_as_moderator(self):
        r = self.signup(user_type="moderator")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="sam").exists())


class RoleTests(TestCase):
    def test_moderator_gets_staff_access_and_loses_it_when_demoted(self):
        u = User.objects.create_user("mod", password=PW, user_type="moderator")
        self.assertTrue(u.is_staff)
        u.user_type = "attendee"
        u.save()
        self.assertFalse(u.is_staff)

    def test_attendee_cannot_post(self):
        u = User.objects.create_user("fan", password=PW)
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("events:create")).status_code, 403)

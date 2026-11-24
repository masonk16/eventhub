from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import PromoterProfile, User


class SignupForm(UserCreationForm):
    # Moderator is deliberately not offered here; staff assign it in the admin.
    user_type = forms.ChoiceField(
        label="I want to",
        choices=[(User.Type.ATTENDEE, "Find events"), (User.Type.PROMOTER, "Post events")],
        initial=User.Type.ATTENDEE,
    )
    organization_name = forms.CharField(
        max_length=150, required=False, label="Organization or promoter name",
        help_text="Required if you want to post events.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean(self):
        data = super().clean()
        if data.get("user_type") == User.Type.PROMOTER and not data.get("organization_name"):
            self.add_error("organization_name", "Tell us who you're posting events for.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data["user_type"]
        user.save()
        if user.user_type == User.Type.PROMOTER:
            PromoterProfile.objects.create(user=user, organization_name=self.cleaned_data["organization_name"])
        return user

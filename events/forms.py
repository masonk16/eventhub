from django import forms

from .models import Event

DT_FORMAT = "%Y-%m-%dT%H:%M"


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "category", "organizer_name", "description",
            "start_at", "end_at",
            "is_online", "online_url", "venue_name", "address", "city", "country",
            "is_free", "price_info", "ticket_url", "ticket_info",
            "official_website", "contact_email", "image_url", "status",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
            "description": forms.Textarea(attrs={"rows": 6}),
            "ticket_info": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("start_at", "end_at"):
            self.fields[name].input_formats = [DT_FORMAT]

    def clean(self):
        data = super().clean()
        start, end = data.get("start_at"), data.get("end_at")
        if start and end and end < start:
            self.add_error("end_at", "The end time must be after the start time.")
        if not data.get("is_online") and not (data.get("city") or data.get("venue_name")):
            self.add_error("city", "Add a venue or city, or mark the event as online.")
        if data.get("is_online") and not data.get("online_url"):
            self.add_error("online_url", "Add the link to join.")
        if not data.get("is_free") and not (data.get("ticket_url") or data.get("ticket_info")):
            self.add_error("ticket_url", "Say where to get tickets, or mark the event as free.")
        return data

    def save(self, commit=True):
        event = super().save(commit=False)
        # Changing the links that proved ownership invalidates the proof.
        if event.pk and event.is_verified and {"official_website", "ticket_url"} & set(self.changed_data):
            event.reset_verification()
        if commit:
            event.save()
        return event


class WebsiteProofForm(forms.Form):
    proof_url = forms.URLField(label="Page that shows the code")


class EmailProofForm(forms.Form):
    email = forms.EmailField(label="Email at your event's domain")


class ManualProofForm(forms.Form):
    evidence = forms.CharField(
        label="How can we confirm you run this event?",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="For example: your role, a sponsor or venue contact, a social account that links to this event.",
    )
    proof_url = forms.URLField(label="Supporting link (optional)", required=False)

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import promoter_required

from . import verification
from .forms import EmailProofForm, EventForm, ManualProofForm, WebsiteProofForm
from .models import Category, Event, VerificationRequest


def event_list(request):
    qs = Event.objects.filter(status=Event.Status.PUBLISHED).select_related("category")
    now = timezone.now()
    get = request.GET

    if get.get("past"):
        qs = qs.filter(start_at__lt=now).order_by("-start_at")
    else:
        qs = qs.filter(Q(start_at__gte=now) | Q(end_at__gte=now))
    if q := get.get("q", "").strip():
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(organizer_name__icontains=q)
                       | Q(venue_name__icontains=q))
    if cat := get.get("category"):
        qs = qs.filter(category__slug=cat)
    if city := get.get("city", "").strip():
        qs = qs.filter(city__icontains=city)
    if get.get("free"):
        qs = qs.filter(is_free=True)
    if get.get("online"):
        qs = qs.filter(is_online=True)
    if get.get("verified"):
        qs = qs.filter(verification_status=Event.Verification.VERIFIED)

    page = Paginator(qs, 12).get_page(get.get("page"))
    keep = {k: v for k, v in get.items() if k != "page" and v}
    return render(request, "events/event_list.html", {
        "page": page, "categories": Category.objects.all(), "qs": urlencode(keep), "filters": get,
    })


def event_detail(request, slug):
    event = get_object_or_404(Event.objects.select_related("category", "owner"), slug=slug)
    if event.status != Event.Status.PUBLISHED and event.owner_id != request.user.id:
        raise Http404
    return render(request, "events/event_detail.html", {"event": event, "is_owner": event.owner_id == request.user.id})


@promoter_required
def event_create(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.owner = request.user
        event.save()
        messages.success(request, "Event posted. Verify it to earn the organizer badge.")
        return redirect("events:verify", slug=event.slug)
    return render(request, "events/event_form.html", {"form": form, "title": "Post an event"})


@promoter_required
def event_edit(request, slug):
    event = get_object_or_404(Event, slug=slug, owner=request.user)
    was_verified = event.is_verified
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        event = form.save()
        if was_verified and not event.is_verified:
            messages.warning(request, "You changed your website or ticket link, so this event needs to be verified again.")
        else:
            messages.success(request, "Changes saved.")
        return redirect(event)
    return render(request, "events/event_form.html", {"form": form, "title": "Edit event", "event": event})


@promoter_required
def event_delete(request, slug):
    event = get_object_or_404(Event, slug=slug, owner=request.user)
    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted.")
        return redirect("events:mine")
    return render(request, "events/event_confirm_delete.html", {"event": event})


@promoter_required
def my_events(request):
    events = Event.objects.filter(owner=request.user).order_by("-start_at")
    return render(request, "events/my_events.html", {"events": events})


@promoter_required
def verify_event(request, slug):
    event = get_object_or_404(Event, slug=slug, owner=request.user)
    if event.is_verified:
        return redirect(event)

    forms = {"website": WebsiteProofForm(prefix="website"), "email": EmailProofForm(prefix="email"),
             "manual": ManualProofForm(prefix="manual")}
    method = request.POST.get("method")

    if request.method == "POST" and method in forms:
        form = forms[method].__class__(request.POST, prefix=method)
        forms[method] = form
        if form.is_valid():
            if method == "website":
                ok, msg = verification.check_website_proof(event, form.cleaned_data["proof_url"])
                if ok:
                    event.mark_verified("website")
                    messages.success(request, "Verified. Your event now shows the organizer badge.")
                    return redirect(event)
                form.add_error("proof_url", msg)
            elif method == "email":
                address = form.cleaned_data["email"]
                ok, msg = verification.check_email_eligibility(event, address)
                if ok:
                    verification.send_email_link(request, event, address)
                    messages.success(request, f"We sent a link to {address}. Open it while signed in.")
                    return redirect("events:verify", slug=event.slug)
                form.add_error("email", msg)
            else:
                VerificationRequest.objects.create(event=event, **form.cleaned_data)
                event.verification_status = Event.Verification.PENDING
                event.save(update_fields=["verification_status", "updated_at"])
                messages.success(request, "Request sent. A reviewer will check it.")
                return redirect("events:verify", slug=event.slug)

    return render(request, "events/verify.html", {
        "event": event, "forms": forms, "requests": event.verification_requests.all()[:5],
    })


@login_required
def verify_email(request, token):
    parsed = verification.read_email_token(token)
    if not parsed:
        messages.error(request, "That link is invalid or has expired. Request a new one.")
        return redirect("events:list")
    event_id, _address = parsed
    event = get_object_or_404(Event, pk=event_id, owner=request.user)
    event.mark_verified("email")
    messages.success(request, "Verified. Your event now shows the organizer badge.")
    return redirect(event)

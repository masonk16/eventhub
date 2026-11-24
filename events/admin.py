from django.contrib import admin
from django.utils import timezone

from .models import Category, Event, VerificationRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer_name", "owner", "start_at", "status", "verification_status")
    list_filter = ("status", "verification_status", "category", "is_free", "is_online")
    search_fields = ("title", "organizer_name", "owner__username", "city")
    readonly_fields = ("verification_token", "verified_at", "created_at", "updated_at")
    actions = ["unpublish", "reset_verification"]

    @admin.action(description="Unpublish selected events")
    def unpublish(self, request, queryset):
        queryset.update(status=Event.Status.DRAFT)

    @admin.action(description="Remove verification from selected events")
    def reset_verification(self, request, queryset):
        for event in queryset:
            event.reset_verification()
            event.save()


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("event", "status", "created_at", "reviewed_by")
    list_filter = ("status",)
    readonly_fields = ("event", "evidence", "proof_url", "created_at", "reviewed_by", "reviewed_at")
    actions = ["approve", "reject"]

    @admin.action(description="Approve: mark events as verified")
    def approve(self, request, queryset):
        for req in queryset.filter(status=VerificationRequest.Status.PENDING):
            req.status = VerificationRequest.Status.APPROVED
            req.reviewed_by, req.reviewed_at = request.user, timezone.now()
            req.save()
            req.event.mark_verified("manual")

    @admin.action(description="Reject (add a reviewer note first if you want one shown)")
    def reject(self, request, queryset):
        for req in queryset.filter(status=VerificationRequest.Status.PENDING):
            req.status = VerificationRequest.Status.REJECTED
            req.reviewed_by, req.reviewed_at = request.user, timezone.now()
            req.save()
            event = req.event
            if not event.is_verified:
                event.verification_status = Event.Verification.UNVERIFIED
                event.save(update_fields=["verification_status", "updated_at"])

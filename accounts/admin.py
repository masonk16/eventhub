from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import PromoterProfile, User


class PromoterProfileInline(admin.StackedInline):
    model = PromoterProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "user_type", "is_staff")
    list_filter = ("user_type", "is_superuser")
    fieldsets = DjangoUserAdmin.fieldsets + (("Role", {"fields": ("user_type",)}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Role", {"fields": ("email", "user_type")}),)
    inlines = [PromoterProfileInline]

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),                # signup (ours) goes first
    path("accounts/", include("django.contrib.auth.urls")),     # login, logout, password reset
    path("", include("events.urls")),
]

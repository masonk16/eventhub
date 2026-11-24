from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("events/new/", views.event_create, name="create"),
    path("events/mine/", views.my_events, name="mine"),
    path("events/verify/email/<str:token>/", views.verify_email, name="verify_email"),
    path("events/<slug:slug>/", views.event_detail, name="detail"),
    path("events/<slug:slug>/edit/", views.event_edit, name="edit"),
    path("events/<slug:slug>/delete/", views.event_delete, name="delete"),
    path("events/<slug:slug>/verify/", views.verify_event, name="verify"),
]

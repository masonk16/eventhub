from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("events:list")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("events:create" if user.is_promoter else "events:list")
    return render(request, "registration/signup.html", {"form": form})

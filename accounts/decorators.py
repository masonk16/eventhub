from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def promoter_required(view):
    """Signed in and a promoter (or superuser). Anyone else gets a 403."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_promoter:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper

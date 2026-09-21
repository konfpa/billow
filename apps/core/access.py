from functools import wraps
from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class MissingPermission(PermissionDenied):
    """A refusal that knows which permission would have let the request in."""

    def __init__(self, permission: str) -> None:
        super().__init__(permission)
        self.permission = permission


def requires(
    permission: str,
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Let a view through only for a User holding `permission`.

    The view is marked with what it declares, so the URLconf can be checked
    for views that declare nothing.
    """

    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(
            request: HttpRequest, *args: object, **kwargs: object
        ) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if not request.user.has_perm(permission):
                raise MissingPermission(permission)

            return view(request, *args, **kwargs)

        wrapped.required_permission = permission
        return wrapped

    return decorator


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    """The refusal, naming what is missing as the admin names it.

    Only a MissingPermission is trusted to say what was needed. Any other
    refusal's message is whatever the raising code typed, written for a log.
    """
    missing = None

    if isinstance(exception, MissingPermission):
        app_label, codename = exception.permission.split(".")
        missing = (
            Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            )
            .values_list("name", flat=True)
            .first()
        )

    return render(request, "403.html", {"missing": missing}, status=403)

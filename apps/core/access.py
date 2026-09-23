from functools import wraps
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import URLResolver, get_resolver

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse
    from django.urls import URLPattern

# Views anyone may reach without a Role: signing in and out, which a User
# needs before any Role could apply; the health check, which is watched by
# machines rather than Users; and home, which every User lands on.
PERMISSION_EXEMPT_URL_NAMES = frozenset({"login", "logout", "healthz", "home"})


class MissingPermission(PermissionDenied):
    """A refusal that knows which permission would have let the request in."""

    def __init__(self, permission: str) -> None:
        super().__init__(permission)
        self.permission = permission


def requires(
    permission: str, *alternatives: str
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Let a view through only for a User holding `permission` or an alternative.

    A refusal names `permission`. The view is marked with what it declares, so
    the URLconf can be checked for views that declare nothing.
    """

    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(
            request: HttpRequest, *args: object, **kwargs: object
        ) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if not any(
                request.user.has_perm(held) for held in (permission, *alternatives)
            ):
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


def undeclared_views(urlconf: str | None = None) -> list[str]:
    """Name every view in `urlconf` that declares no permission and is not exempt.

    The admin checks its own permissions and static and media are files rather
    than billow's views, so they are passed over as the setup gate passes them.
    """
    files = (settings.STATIC_URL.lstrip("/"), settings.MEDIA_URL.lstrip("/"))

    return [
        pattern.name or route
        for route, pattern in _walk(get_resolver(urlconf).url_patterns)
        if pattern.name not in PERMISSION_EXEMPT_URL_NAMES
        and not route.startswith(files)
        and not hasattr(pattern.callback, "required_permission")
    ]


def _walk(
    patterns: list[URLPattern | URLResolver], prefix: str = ""
) -> list[tuple[str, URLPattern]]:
    found = []

    for pattern in patterns:
        route = prefix + str(pattern.pattern).lstrip("^")

        if not isinstance(pattern, URLResolver):
            found.append((route, pattern))
        elif pattern.app_name != "admin":
            found.extend(_walk(pattern.url_patterns, route))

    return found

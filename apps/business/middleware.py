from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render

from apps.business.models import Business

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

# Reachable while the gate is closed: the front door, without which nobody
# could sign in to finish setup; the setup page itself, which would otherwise
# redirect to itself; and the health check, because a half-configured
# deployment must still report as alive to whatever is watching it. The admin
# is let through by its namespace rather than by name, and static and media by
# their paths.
OPEN_URL_NAMES = frozenset({"login", "logout", "healthz", "business_settings"})


class SetupGateMiddleware:
    """Hold billow shut until it knows whose name goes on the invoice.

    A gate rather than a decorator, so that a view added later is covered by
    having been written at all, instead of by someone remembering to opt it in.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        _view_func: Callable[..., HttpResponse],
        _view_args: tuple[object, ...],
        _view_kwargs: dict[str, object],
    ) -> HttpResponse | None:
        # Run here rather than in __call__ because this is the earliest point
        # at which the request has been matched to a URL, and the exempt paths
        # are named URLs rather than spellings of a path.
        if self.is_open(request):
            return None

        if not Business.load().missing_for_setup():
            return None

        if not request.user.is_authenticated:
            # Gated rather than left to the view's own login_required, so that
            # a view added later is covered whether or not it asks to be.
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return redirect("business_settings")

        # Bouncing an Operator to the setup page would land them on a 403 they
        # cannot do anything about, so they get the reason instead.
        return render(request, "business/setup_needed.html")

    def is_open(self, request: HttpRequest) -> bool:
        match = request.resolver_match

        if match and (match.url_name in OPEN_URL_NAMES or match.app_name == "admin"):
            return True

        return request.path.startswith((settings.STATIC_URL, settings.MEDIA_URL))

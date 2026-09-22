from typing import TYPE_CHECKING

from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def back(request: HttpRequest, fallback: str, **kwargs: object) -> HttpResponse:
    """Return to the page an act was taken from, or else to the fallback.

    A directory's row menu posts where it was, so archiving from the list
    lands back on the list. Only a path on this site is followed, or a forged
    form could send an Operator anywhere.
    """
    target = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(fallback, **kwargs)

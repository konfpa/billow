from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from apps.business.forms import BusinessForm
from apps.business.models import Business

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@login_required
def business_settings(request: HttpRequest) -> HttpResponse:
    """The Business's details: read by any Operator, written by a Superuser.

    An Operator who is not a Superuser is shown what appears on invoices,
    because checking it is part of their job; the form is simply not there
    for them, and a request that tries to write anyway is refused.
    """
    business = Business.load()

    if request.method != "POST":
        return render(
            request,
            "business/settings.html",
            {"business": business, "form": BusinessForm(instance=business)},
        )

    if not request.user.is_superuser:
        raise PermissionDenied

    # Bound to its own instance: a form that fails validation still writes
    # what it could clean onto the instance it holds, and `business` is what
    # the page shows as stored — the logo preview included.
    form = BusinessForm(request.POST, request.FILES, instance=Business.load())

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(
            request,
            "business/settings.html",
            {"business": business, "form": form},
        )

    form.save()
    messages.success(request, "The Business's details are saved.")
    return redirect("business_settings")

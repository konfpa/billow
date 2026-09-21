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

    While billow is still incomplete this is the setup page, and only a
    Superuser may see it at all. Once complete it is the ordinary settings
    page: an Operator who is not a Superuser is shown what appears on
    invoices, because checking it is part of their job; the form is simply not
    there for them, and a request that tries to write anyway is refused.
    """
    business = Business.load()

    if business.missing_for_setup() and not request.user.is_superuser:
        raise PermissionDenied

    if request.method != "POST":
        return settings_page(request, business, BusinessForm(instance=business))

    if not request.user.is_superuser:
        raise PermissionDenied

    # Bound to its own instance: a form that fails validation still writes
    # what it could clean onto the instance it holds, and `business` is what
    # the page shows as stored — the logo preview included.
    form = BusinessForm(request.POST, request.FILES, instance=Business.load())

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return settings_page(request, business, form)

    form.save()
    messages.success(request, "The Business's details are saved.")
    return redirect("business_settings")


def settings_page(
    request: HttpRequest, business: Business, form: BusinessForm
) -> HttpResponse:
    """The page, naming whatever setup is still waiting on.

    What is missing is read off the stored Business rather than off the form,
    because the question the gate asks is what billow holds, not what this
    submission carried.
    """
    return render(
        request,
        "business/settings.html",
        {
            "business": business,
            "form": form,
            "missing": business.what_setup_still_needs(),
            "last_change": business.history.first() if business.pk else None,
        },
    )

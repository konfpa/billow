from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.customers.forms import CustomerForm
from apps.customers.models import Customer

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@login_required
def customer_directory(request: HttpRequest) -> HttpResponse:
    """Everyone billow can invoice."""
    return render(
        request,
        "customers/directory.html",
        {"customers": Customer.objects.all()},
    )


@login_required
def record_customer(request: HttpRequest) -> HttpResponse:
    """Put a new Customer on file."""
    if request.method != "POST":
        return render(request, "customers/record.html", {"form": CustomerForm()})

    form = CustomerForm(request.POST)

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(request, "customers/record.html", {"form": form})

    customer = form.save()
    messages.success(request, f"{customer.name} is recorded.")
    return redirect("customer_directory")

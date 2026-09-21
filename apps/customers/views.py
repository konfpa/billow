from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

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
    messages.success(request, f"{customer.name} is saved.")
    return redirect("customer_directory")


@login_required
def edit_customer(request: HttpRequest, pk: int) -> HttpResponse:
    """Correct what is on file about a Customer.

    Every rule that applies to recording applies here, the GSTIN included: a
    wrong recipient GSTIN cannot be amended in GSTR-1A, so a typo caught later
    has to be fixable rather than worked around with a second Customer. What is
    corrected here is the Customer and nothing else; see
    docs/adr/0007-invoices-snapshot-the-recipient.md.
    """
    customer = get_object_or_404(Customer, pk=pk)

    if request.method != "POST":
        form = CustomerForm(instance=customer)
        return render(
            request,
            "customers/edit.html",
            {"form": form, "customer": customer},
        )

    # Bound to its own instance: a form that fails validation still writes what
    # it could clean onto the instance it holds, and `customer` is what the
    # page shows as on file.
    form = CustomerForm(request.POST, instance=Customer.objects.get(pk=pk))

    if not form.is_valid():
        # Rendered rather than redirected, so that everything already typed is
        # still on the page next to what was wrong with it.
        return render(
            request,
            "customers/edit.html",
            {"form": form, "customer": customer},
        )

    form.save()
    messages.success(request, f"{form.instance.name} is saved.")
    return redirect("customer_directory")

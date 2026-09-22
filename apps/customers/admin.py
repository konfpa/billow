from typing import TYPE_CHECKING

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.customers.models import Customer

if TYPE_CHECKING:
    from django.http import HttpRequest

    from apps.core.models import CounterpartyQuerySet


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    """Customers, shown here and changed elsewhere.

    The directory pages are the only writing surface, so that the GSTIN
    checksum and state checks cannot be walked around from the admin at eleven
    at night. What the admin adds is the history: who changed a Customer's
    address, and when.
    """

    fields = (
        "name",
        "legal_name",
        "address",
        "city",
        "postal_code",
        "state",
        "gstin",
        "email",
        "phone",
        "archived_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    list_display = ("name", "legal_name", "city", "state", "gstin", "archived_at")

    def get_queryset(self, request: HttpRequest) -> CounterpartyQuerySet:  # noqa: ARG002
        # The default manager leaves the archived out, and the admin is where
        # a Superuser goes to read what happened to one.
        return Customer.including_archived.all()

    def has_add_permission(self, request: HttpRequest) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(
        self,
        request: HttpRequest,  # noqa: ARG002
        obj: object = None,  # noqa: ARG002
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,  # noqa: ARG002
        obj: object = None,  # noqa: ARG002
    ) -> bool:
        return False

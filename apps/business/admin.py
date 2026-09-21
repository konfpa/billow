from typing import TYPE_CHECKING

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.business.models import Business

if TYPE_CHECKING:
    from django.http import HttpRequest


@admin.register(Business)
class BusinessAdmin(SimpleHistoryAdmin):
    """The Business, shown here and changed elsewhere.

    The settings page is the only writing surface, so that the GSTIN checks
    cannot be walked around from the admin at eleven at night. What the admin
    adds is the history: who changed a detail, and when.
    """

    fields = (
        "name",
        "legal_name",
        "address",
        "city",
        "postal_code",
        "state",
        "is_gst_registered",
        "gstin",
        "pan",
        "cin",
        "email",
        "phone",
        "website",
        "logo",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    list_display = ("name", "state", "is_gst_registered", "gstin")

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

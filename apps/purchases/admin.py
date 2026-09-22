from typing import TYPE_CHECKING

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.purchases.models import Purchase, PurchaseLine

if TYPE_CHECKING:
    from django.http import HttpRequest


class ReadOnlyAdmin:
    """Shown here and recorded elsewhere, as Items are.

    The Purchase pages are the only writing surface, so that a line's unit and
    the Supplier's registration copied onto the bill cannot be walked around.
    """

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False


class PurchaseLineInline(ReadOnlyAdmin, admin.TabularInline):
    model = PurchaseLine
    fields = (
        "item",
        "name",
        "hsn_sac",
        "unit",
        "stock_units_in_one",
        "quantity",
        "rate",
        "discount_percent",
        "gst_rate",
    )
    readonly_fields = fields


@admin.register(Purchase)
class PurchaseAdmin(ReadOnlyAdmin, SimpleHistoryAdmin):
    fields = (
        "supplier",
        "bill_number",
        "bill_date",
        "received_date",
        "supplier_gstin",
        "supplier_state",
        "bill_discount",
        "round_off",
        "billed_total",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    list_display = ("bill_number", "supplier", "bill_date", "received_date")
    list_select_related = ("supplier",)
    inlines = (PurchaseLineInline,)

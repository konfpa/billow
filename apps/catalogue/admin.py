from typing import TYPE_CHECKING

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.catalogue.models import Item, ItemUnit

if TYPE_CHECKING:
    from django.http import HttpRequest


class ReadOnlyAdmin:
    """Shown here and changed elsewhere, as Customers are.

    The catalogue pages are the only writing surface, so that the HSN/SAC and
    rate checks cannot be walked around from the admin.
    """

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: ARG002
        return False


class ItemUnitInline(ReadOnlyAdmin, admin.TabularInline):
    model = ItemUnit
    fields = ("code", "rate", "is_stock_unit", "selling_price", "mrp")
    readonly_fields = fields


@admin.register(Item)
class ItemAdmin(ReadOnlyAdmin, SimpleHistoryAdmin):
    fields = ("code", "name", "kind", "hsn_sac", "gst_rate", "created_at", "updated_at")
    readonly_fields = fields
    list_display = ("code", "name", "kind", "hsn_sac", "gst_rate")
    inlines = (ItemUnitInline,)

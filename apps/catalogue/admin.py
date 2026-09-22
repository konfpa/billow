from typing import TYPE_CHECKING

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.catalogue.models import Brand, Category, Item, ItemUnit

if TYPE_CHECKING:
    from django.http import HttpRequest

    from apps.catalogue.models import ItemQuerySet


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
    fields = (
        "code",
        "name",
        "kind",
        "brand",
        "category",
        "hsn_sac",
        "gst_rate",
        "archived_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    list_display = (
        "code",
        "name",
        "kind",
        "brand",
        "category",
        "hsn_sac",
        "gst_rate",
        "archived_at",
    )
    list_filter = ("brand", "category")
    inlines = (ItemUnitInline,)

    def get_queryset(self, request: HttpRequest) -> ItemQuerySet:  # noqa: ARG002
        # The default manager leaves the archived out, and the admin is where
        # a Superuser goes to read what happened to one.
        return Item.including_archived.all()


@admin.register(Brand)
class BrandAdmin(ReadOnlyAdmin, admin.ModelAdmin):
    fields = ("name",)
    readonly_fields = fields
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(ReadOnlyAdmin, admin.ModelAdmin):
    fields = ("name", "parent")
    readonly_fields = fields
    list_display = ("__str__", "parent")
    list_select_related = ("parent",)
    search_fields = ("name", "parent__name")

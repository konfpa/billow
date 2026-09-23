from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from apps.catalogue.models import Item, ItemQuerySet, ItemUnit
from apps.core.forms import LINE_CONTROL, LINE_SELECT, LINE_TEXT, StyledForm
from apps.purchases.models import Purchase, PurchaseLine
from apps.tax.rates import GSTRate


def items_on_file() -> ItemQuerySet:
    return Item.objects.prefetch_related("units")


def units_of(item: Item) -> list[ItemUnit]:
    """The Item's units, its stock unit first, as a line offers them."""
    return sorted(item.units.all(), key=lambda unit: (not unit.is_stock_unit, unit.pk))


def blank_when_none(form: forms.ModelForm, name: str) -> None:
    """An optional discount, shown empty rather than as 0 when there is none."""
    form.fields[name].required = False
    if not form.initial.get(name):
        form.initial[name] = None


class PurchaseLineForm(StyledForm):
    # Chosen by the line's Item picker rather than typed, and offered as the
    # chosen Item's own units, so it is checked against that Item in clean().
    unit = forms.CharField(widget=forms.Select, required=False)

    class Meta:
        model = PurchaseLine
        fields = (
            "item",
            "name",
            "hsn_sac",
            "unit",
            "quantity",
            "rate",
            "discount_percent",
            "gst_rate",
        )
        labels = {
            "name": "Name",
            "rate": "Rate",
            "discount_percent": "Discount",
            "gst_rate": "GST",
        }
        widgets = {
            "item": forms.HiddenInput,
            "name": forms.TextInput(attrs={"placeholder": "Freight, loading…"}),
            "hsn_sac": forms.TextInput(
                attrs={"inputmode": "numeric", "placeholder": "HSN/SAC"}
            ),
            "quantity": forms.TextInput(attrs={"inputmode": "decimal"}),
            "rate": forms.TextInput(attrs={"inputmode": "decimal"}),
            "discount_percent": forms.TextInput(attrs={"inputmode": "decimal"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        # A line keeps the Item it already names, even one Archived since.
        self.fields["item"].queryset = Item.including_archived.filter(
            models.Q(archived_at__isnull=True) | models.Q(pk=self.instance.item_id)
        ).prefetch_related("units")
        self.fields["item"].error_messages["invalid_choice"] = (
            "Choose an Item on file from the list."
        )
        # Left blank, the line takes the Item's own rate.
        self.fields["gst_rate"].required = False
        self.fields["gst_rate"].choices = [("", "Item's"), *GSTRate.choices]
        blank_when_none(self, "discount_percent")

        for name in ("unit", "gst_rate"):
            self.fields[name].widget.attrs["class"] = LINE_SELECT
        for name in ("quantity", "rate", "discount_percent"):
            self.fields[name].widget.attrs["class"] = LINE_CONTROL
        for name in ("name", "hsn_sac"):
            self.fields[name].widget.attrs["class"] = LINE_TEXT

    @property
    def is_one_off(self) -> bool:
        """Whether this is a One-off line rather than an Item line.

        Read off which row was posted, since only a One-off row sends a name
        and a code, so a row left without its Item is told to choose one rather
        than to name itself.
        """
        if self.is_bound:
            return any(
                self.add_prefix(name) in self.data for name in ("name", "hsn_sac")
            )
        return self.instance.pk is not None and self.instance.item_id is None

    @property
    def gst_rate_options(self) -> list[tuple[str, str]]:
        """A One-off line's GST rates: it has no Item's rate to fall back on."""
        return [(str(value), label) for value, label in GSTRate.choices]

    @property
    def chosen_item(self) -> Item | None:
        """The Item this line names, for drawing the row before it is cleaned."""
        raw = self["item"].value()
        if isinstance(raw, Item):
            return raw
        if not str(raw or "").isdigit():
            return None
        return self.fields["item"].queryset.filter(pk=raw).first()

    @property
    def unit_options(self) -> list[str]:
        item = self.chosen_item
        if item is None:
            return []
        codes = [unit.code for unit in units_of(item)]
        if (
            self.recorded_in(item, self.instance.unit)
            and self.instance.unit not in codes
        ):
            codes.append(self.instance.unit)
        return codes

    def recorded_in(self, item: Item, unit: str) -> bool:
        """Whether this line is on file as `item` billed in `unit`.

        Such a line keeps the conversion it was recorded with, so correcting a
        bill never recounts it through the Item's units as they are now.
        """
        return (
            self.instance.pk is not None
            and self.instance.item_id == item.pk
            and self.instance.unit == unit
        )

    def clean(self) -> dict:
        cleaned = super().clean()
        if self.is_one_off:
            return self.clean_one_off(cleaned)

        item = cleaned.get("item")
        if item is None:
            if "item" not in self.errors:
                self.add_error("item", self.fields["item"].error_messages["required"])
            return cleaned

        unit = next(
            (unit for unit in item.units.all() if unit.code == cleaned.get("unit")),
            None,
        )
        if not self.recorded_in(item, cleaned.get("unit")):
            if unit is None:
                self.add_error("unit", f"Choose one of the units {item.name} is in.")
            else:
                self.instance.stock_units_in_one = unit.rate

        if cleaned.get("gst_rate") in (None, ""):
            cleaned["gst_rate"] = item.gst_rate
        return cleaned

    def clean_one_off(self, cleaned: dict) -> dict:
        if self["item"].value():
            self.add_error(
                "name", "A line is either an Item or a One-off line, never both."
            )
            return cleaned

        required = {
            "name": "Name the line as the bill does.",
            "hsn_sac": "Give the HSN or SAC the bill prints.",
            "gst_rate": "Choose the GST rate the bill charges.",
        }
        for name, message in required.items():
            if name not in self.errors and cleaned.get(name) in (None, ""):
                self.add_error(name, message)
        cleaned["unit"] = ""
        return cleaned

    def clean_discount_percent(self) -> Decimal:
        return self.cleaned_data["discount_percent"] or Decimal(0)


class PurchaseLineFormSet(forms.BaseInlineFormSet):
    def kept_forms(self) -> list[PurchaseLineForm]:
        """The lines the Purchase keeps: those filled in, less any removed."""
        return [
            form
            for form in self.forms
            if (form in self.initial_forms or form.has_changed())
            and not self._should_delete_form(form)
        ]

    def clean(self) -> None:
        if not self.kept_forms():
            msg = "Add at least one line, as the bill lists them."
            raise ValidationError(msg)


LineFormSet = forms.inlineformset_factory(
    Purchase,
    PurchaseLine,
    form=PurchaseLineForm,
    formset=PurchaseLineFormSet,
    extra=1,
)

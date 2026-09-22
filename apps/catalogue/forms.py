from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalogue.models import Item, ItemUnit
from apps.core.forms import LINE_CONTROL, LINE_SELECT, StyledForm
from apps.core.templatetags.ui import plain
from apps.tax.rates import GSTRate
from apps.tax.units import UNITS


class ItemCodeField(forms.CharField):
    """An Item code, folded to capitals before anything checks it.

    A lower-case entry is a keyboard state rather than a different code, and
    both must find the same Item when a label is scanned. Only plain letters
    are folded, since some others capitalise into them, as ß does into SS.
    """

    def to_python(self, value: object) -> str:
        code = super().to_python(value) or ""
        return code.upper() if code.isascii() else code


class RateInput(forms.TextInput):
    """A rate stored to six places, shown as typed: 20, not 20.000000."""

    def format_value(self, value: object) -> str | None:
        if isinstance(value, Decimal):
            return plain(value)
        return super().format_value(value)


class ItemUnitForm(StyledForm):
    """A further unit, defined by its rate against the stock unit."""

    class Meta:
        model = ItemUnit
        fields = ("code", "rate", "selling_price")
        # "Rate" meant nothing to an Operator; what they know is that one
        # piece holds 20 ft.
        labels = {"rate": "Stock units in one", "selling_price": "Selling price"}
        widgets = {
            "rate": RateInput(attrs={"inputmode": "decimal"}),
            "selling_price": forms.TextInput(attrs={"inputmode": "decimal"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["code"].choices = [("", "Choose a unit"), *UNITS]
        # Without the model's default of 1, a blank row is unchanged and so
        # skipped, rather than a half-filled unit that fails.
        self.fields["rate"].initial = None

        self.fields["code"].widget.attrs["class"] = LINE_SELECT
        for name in ("rate", "selling_price"):
            self.fields[name].widget.attrs["class"] = LINE_CONTROL

    def clean(self) -> dict:
        cleaned = super().clean()
        # Judged by the formset against what is posted instead: checked
        # against the units on file, a unit removed and re-added in one edit
        # would clash with itself.
        self._validate_unique = False
        self._validate_constraints = False
        return cleaned


class ItemUnitFormSet(forms.BaseInlineFormSet):
    """The units beyond the stock unit, judged against the Item form beside it."""

    item_form: ItemForm

    def kept_forms(self) -> list[ItemUnitForm]:
        """The rows the Item keeps: those on file or filled in, less any removed."""
        return [
            form
            for form in self.forms
            if (form in self.initial_forms or form.has_changed())
            and not self._should_delete_form(form)
        ]

    def clean(self) -> None:
        # Replaces the model formset's own uniqueness check, which cannot see
        # the stock unit chosen on the Item form.
        item = getattr(self.item_form, "cleaned_data", {})
        kept = self.kept_forms()

        if item.get("kind") == Item.Kind.SERVICE and kept:
            msg = "A Service is sold in one unit, so it has no further units."
            raise ValidationError(msg)

        seen = {item.get("stock_unit")}
        for form in kept:
            code = form.cleaned_data.get("code")
            if code and code in seen:
                form.add_error("code", "This Item already has this unit.")
            seen.add(code)


UnitFormSet = forms.inlineformset_factory(
    Item, ItemUnit, form=ItemUnitForm, formset=ItemUnitFormSet, extra=0
)


class ItemForm(StyledForm):
    """An Item, its stock unit and any further units, recorded and edited together."""

    stock_unit = forms.ChoiceField(
        choices=[("", "Choose a unit"), *UNITS],
        help_text="The unit the Item is sold in, and its stock counted in.",
    )
    selling_price = forms.DecimalField(
        label="Selling price",
        max_digits=12,
        decimal_places=2,
        min_value=0,
        help_text="Per stock unit, including GST.",
    )

    class Meta:
        model = Item
        fields = ("name", "kind", "code", "hsn_sac", "gst_rate")
        field_classes = {"code": ItemCodeField}
        labels = {"name": "Name"}
        help_texts = {"code": "Leave blank for billow to assign the next one."}

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # One list decides what an Item must answer, so a release that
            # adds a requirement changes the model and this form follows.
            field.required = name in Item.REQUIRED_TO_RECORD

        # A ModelForm's choice field takes no empty_label, so the prompt
        # replaces the blank choice Django puts in front of the choices.
        self.fields["kind"].choices = [
            ("", "Choose Goods or Service"),
            *Item.Kind.choices,
        ]
        self.fields["gst_rate"].choices = [("", "Choose a rate"), *GSTRate.choices]

        if unit := self.instance.stock_unit if self.instance.pk else None:
            self.initial.setdefault("stock_unit", unit.code)
            self.initial.setdefault("selling_price", unit.selling_price)

        if self.instance.pk:
            self.fields["code"].help_text = "Leave blank to keep the code on file."

        self.units = UnitFormSet(
            self.data if self.is_bound else None,
            instance=self.instance,
            queryset=ItemUnit.objects.filter(is_stock_unit=False),
            prefix="units",
        )
        self.units.item_form = self

    def is_valid(self) -> bool:
        # The Item first: its kind and stock unit are what the units are
        # judged against.
        item_is_valid = super().is_valid()
        return self.units.is_valid() and item_is_valid

    @property
    def summary(self) -> list[tuple[str, forms.BoundField]]:
        """Every field that failed, the units' included, labelled for the summary."""
        if not self.is_bound:
            return []

        failed = [(field.label, field) for field in self.invalid_fields]
        for form in self.units.kept_forms():
            position = self.units.forms.index(form) + 1
            failed += [
                (f"Further unit {position}, {field.label.lower()}", field)
                for field in form
                if field.errors
            ]
        return failed

    def clean_code(self) -> str:
        return self.cleaned_data["code"] or self.instance.code

    @transaction.atomic
    def save(self) -> Item:
        item = super().save()
        unit = item.stock_unit or ItemUnit(item=item, is_stock_unit=True)

        # Saved only when changed, so the unit's history holds real changes.
        if not unit.pk or {"stock_unit", "selling_price"} & set(self.changed_data):
            # The stock unit changes freely while no stock movements exist; see
            # docs/adr/0011-stock-is-the-sum-of-movements.md.
            unit.code = self.cleaned_data["stock_unit"]
            unit.selling_price = self.cleaned_data["selling_price"]
            unit.save()

        self.units.save()
        return item

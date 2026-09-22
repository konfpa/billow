import json
from dataclasses import dataclass
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateformat import format as date_format

from apps.business.models import Business
from apps.catalogue.models import Item, ItemQuerySet, ItemUnit
from apps.core.forms import LINE_CONTROL, LINE_SELECT, StyledForm
from apps.core.templatetags.ui import plain, rupees
from apps.purchases.models import Purchase, PurchaseLine
from apps.suppliers.models import Supplier
from apps.tax.rates import GSTRate


def goods_on_file() -> ItemQuerySet:
    return Item.objects.filter(kind=Item.Kind.GOODS).prefetch_related("units")


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
    unit = forms.CharField(widget=forms.Select)

    class Meta:
        model = PurchaseLine
        fields = ("item", "unit", "quantity", "rate", "discount_percent", "gst_rate")
        labels = {"rate": "Rate", "discount_percent": "Discount", "gst_rate": "GST"}
        widgets = {
            "item": forms.HiddenInput,
            "quantity": forms.TextInput(attrs={"inputmode": "decimal"}),
            "rate": forms.TextInput(attrs={"inputmode": "decimal"}),
            "discount_percent": forms.TextInput(attrs={"inputmode": "decimal"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = goods_on_file()
        self.fields["item"].error_messages["invalid_choice"] = (
            "Choose Goods on file from the list."
        )
        # Left blank, the line takes the Item's own rate.
        self.fields["gst_rate"].required = False
        self.fields["gst_rate"].choices = [("", "Item's"), *GSTRate.choices]
        blank_when_none(self, "discount_percent")

        for name in ("unit", "gst_rate"):
            self.fields[name].widget.attrs["class"] = LINE_SELECT
        for name in ("quantity", "rate", "discount_percent"):
            self.fields[name].widget.attrs["class"] = LINE_CONTROL

    @property
    def chosen_item(self) -> Item | None:
        """The Item this line names, for drawing the row before it is cleaned."""
        raw = self["item"].value()
        if isinstance(raw, Item):
            return raw
        if not str(raw or "").isdigit():
            return None
        return goods_on_file().filter(pk=raw).first()

    @property
    def unit_options(self) -> list[str]:
        item = self.chosen_item
        return [unit.code for unit in units_of(item)] if item else []

    def clean(self) -> dict:
        cleaned = super().clean()
        item = cleaned.get("item")
        if item is None:
            return cleaned

        unit = next(
            (unit for unit in item.units.all() if unit.code == cleaned.get("unit")),
            None,
        )
        if unit is None:
            self.add_error("unit", f"Choose one of the units {item.name} is in.")
        else:
            self.instance.stock_units_in_one = unit.rate

        if cleaned.get("gst_rate") in (None, ""):
            cleaned["gst_rate"] = item.gst_rate
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


@dataclass(frozen=True)
class TotalCheck:
    """billow's grand total against the one typed off the bill, when they differ."""

    calculated: Decimal
    billed: Decimal

    @property
    def difference(self) -> Decimal:
        return abs(self.calculated - self.billed)

    @property
    def confirmation(self) -> str:
        """What the Operator posts to save these two figures as they stand."""
        return f"{self.billed:.2f}|{self.calculated:.2f}"


class PurchaseForm(StyledForm):
    """A Supplier's bill and its lines, recorded together."""

    # Holds the TotalCheck the Operator saved past. Any change to either total
    # makes it stale, so a confirmation is never carried over to other figures.
    confirmed_total = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Purchase
        fields = (
            "supplier",
            "bill_number",
            "bill_date",
            "received_date",
            "bill_discount",
            "round_off",
            "billed_total",
        )
        labels = {"supplier": "Supplier", "bill_number": "Bill number"}
        widgets = {
            "bill_date": forms.DateInput(attrs={"type": "date"}),
            "received_date": forms.DateInput(attrs={"type": "date"}),
            "bill_discount": forms.TextInput(attrs={"inputmode": "decimal"}),
            "round_off": forms.TextInput(
                attrs={"inputmode": "decimal", "x-bind:placeholder": "roundOffHint"}
            ),
            "billed_total": forms.TextInput(attrs={"inputmode": "decimal"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        # The default manager leaves Archived Suppliers out of the choice.
        self.fields["supplier"].empty_label = "Choose a Supplier"
        self.fields["received_date"].required = False
        blank_when_none(self, "bill_discount")
        # Blank on a new bill, so it takes the suggestion unless one is typed.
        self.fields["round_off"].required = False
        if self.instance.pk is None:
            self.initial["round_off"] = None
        self.total_check: TotalCheck | None = None

        self.lines = LineFormSet(
            self.data if self.is_bound else None,
            instance=self.instance,
            prefix="lines",
        )

    def is_valid(self) -> bool:
        purchase_is_valid = super().is_valid()
        lines_are_valid = self.lines.is_valid()
        if purchase_is_valid and lines_are_valid:
            self.check_bill_discount()
        if lines_are_valid and not self.errors:
            self.check_total()
        return lines_are_valid and not self.errors and not self.total_check

    def check_total(self) -> None:
        # A warning rather than an error: a Supplier who added the bill up
        # wrongly still has to be recorded as billed, once the Operator says so.
        purchase = self.instance
        purchase.copy_supplier()
        lines = [form.instance.as_line() for form in self.lines.kept_forms()]
        suggest = self.cleaned_data["round_off"] is None
        if suggest:
            purchase.round_off = Decimal(0)
        totals = purchase.totals(lines=lines)
        if suggest:
            purchase.round_off = totals.suggested_round_off

        check = TotalCheck(
            calculated=totals.amount + purchase.round_off,
            billed=self.cleaned_data["billed_total"],
        )
        if (
            check.calculated != check.billed
            and self.cleaned_data["confirmed_total"] != check.confirmation
        ):
            self.total_check = check

    def check_bill_discount(self) -> None:
        # Needs the lines cleaned, so it runs once both forms are.
        after_line_discounts = sum(
            (form.instance.as_line().discounted for form in self.lines.kept_forms()),
            Decimal(0),
        )
        if self.cleaned_data["bill_discount"] > after_line_discounts:
            self.add_error(
                "bill_discount",
                "A Bill discount is no more than the lines come to after their "
                f"own discounts, {rupees(after_line_discounts)}.",
            )

    def clean_bill_discount(self) -> Decimal:
        return self.cleaned_data["bill_discount"] or Decimal(0)

    def clean(self) -> dict:
        cleaned = super().clean()
        if not cleaned.get("received_date"):
            cleaned["received_date"] = cleaned.get("bill_date")

        bill = [cleaned.get(name) for name in ("supplier", "bill_number", "bill_date")]
        if all(bill):
            on_file = Purchase.objects.same_bill(*bill).exclude(pk=self.instance.pk)
            if existing := on_file.first():
                self.add_error(
                    "bill_number",
                    f"Bill {existing} dated {date_format(existing.bill_date, 'j M Y')} "
                    "is already on file.",
                )
        return cleaned

    @property
    def summary(self) -> list[tuple[str, forms.BoundField]]:
        """Every field that failed, the lines' included, labelled for the summary."""
        if not self.is_bound:
            return []

        failed = [(field.label, field) for field in self.invalid_fields]
        for position, form in enumerate(self.lines.kept_forms(), start=1):
            failed += [
                (f"Line {position}, {field.label.lower()}", field)
                for field in form
                if field.errors
            ]
        return failed

    @property
    def item_options(self) -> list[dict]:
        """Goods on file for the line pickers, searchable by name, code and Brand."""
        return [
            {
                "id": item.pk,
                "name": item.name,
                "code": item.code,
                "brand": item.brand.name if item.brand else "",
                "gstRate": str(item.gst_rate),
                "units": [
                    {"code": unit.code, "rate": plain(unit.rate)}
                    for unit in units_of(item)
                ],
            }
            for item in goods_on_file().select_related("brand")
        ]

    @property
    def tax_context(self) -> str:
        """What the running totals need to split tax as the server will."""
        business = Business.load()
        return json.dumps(
            {
                "businessState": business.state,
                "suppliers": {
                    supplier.pk: {"state": supplier.state, "gstin": supplier.gstin}
                    for supplier in Supplier.objects.all()
                },
            }
        )

    @transaction.atomic
    def save(self) -> Purchase:
        purchase = super().save(commit=False)
        purchase.copy_supplier()
        purchase.save()
        self.lines.instance = purchase
        self.lines.save()
        return purchase

import json
from dataclasses import dataclass
from decimal import Decimal

from django import forms
from django.db import models, transaction
from django.utils.dateformat import format as date_format

from apps.business.models import Business
from apps.core.forms import StyledForm
from apps.core.templatetags.ui import rupees
from apps.purchases.line_forms import LineFormSet, blank_when_none, items_on_file
from apps.purchases.models import Purchase
from apps.suppliers.models import Supplier


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
        # Archived Suppliers are left out of the choice, except the one a bill
        # on file already names.
        self.fields["supplier"].queryset = Supplier.including_archived.filter(
            models.Q(archived_at__isnull=True) | models.Q(pk=self.instance.supplier_id)
        )
        self.fields["supplier"].empty_label = "Choose a Supplier"
        # Read now, since validating writes the posted Supplier onto the instance.
        self.recorded_supplier = {
            "pk": self.instance.supplier_id,
            "state": self.instance.supplier_state,
            "gstin": self.instance.supplier_gstin,
        }
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
        # A bill on file opens with its own lines and no blank one below them.
        if self.instance.pk is not None:
            self.lines.extra = 0

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
        self.copy_supplier()
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
    def item_count(self) -> int:
        """How many Items a line picker's search has to choose from.

        A count, not the Items themselves: they are searched on the server and
        a picker only ever holds what it matched. See item_options in views.
        """
        return items_on_file().count()

    @property
    def tax_context(self) -> str:
        """What the running totals need to split tax as the server will."""
        business = Business.load()
        suppliers = {
            supplier.pk: {"state": supplier.state, "gstin": supplier.gstin}
            for supplier in self.fields["supplier"].queryset
        }
        recorded = self.recorded_supplier
        if recorded["pk"] is not None:
            suppliers[recorded["pk"]] = {
                "state": recorded["state"],
                "gstin": recorded["gstin"],
            }
        return json.dumps({"businessState": business.state, "suppliers": suppliers})

    def copy_supplier(self) -> None:
        """Copy the Supplier's registration onto a new bill, or one moved to them.

        A correction otherwise keeps the registration the bill was recorded
        with; see docs/adr/0007-invoices-snapshot-the-recipient.md.
        """
        if self.instance.supplier_id != self.recorded_supplier["pk"]:
            self.instance.copy_supplier()

    @transaction.atomic
    def save(self) -> Purchase:
        purchase = super().save(commit=False)
        self.copy_supplier()
        purchase.save()
        self.lines.instance = purchase
        self.lines.save()
        purchase.move_stock()
        return purchase

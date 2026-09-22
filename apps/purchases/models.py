from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import ExtractMonth, ExtractYear
from django.db.models.lookups import LessThan
from simple_history.models import HistoricalRecords

from apps.business.models import Business
from apps.catalogue.models import Item
from apps.core.models import state_field
from apps.purchases.totals import Line, Totals, purchase_totals
from apps.suppliers.models import Supplier
from apps.tax.rates import GSTRate
from apps.tax.units import UNITS

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal


def validate_positive(quantity: Decimal) -> None:
    # Goods sent back are a debit note, never a negative line. See
    # docs/adr/0013-a-purchase-is-corrected-in-place.md.
    if quantity <= 0:
        msg = "A quantity is more than zero."
        raise ValidationError(msg)


APRIL = 4


def financial_year(date: str | models.Expression) -> models.Expression:
    """The year the April-to-March financial year of a date starts in."""
    return ExtractYear(date) - models.Case(
        models.When(LessThan(ExtractMonth(date), APRIL), then=1), default=0
    )


class PurchaseQuerySet(models.QuerySet):
    def same_bill(
        self, supplier: Supplier, bill_number: str, bill_date: datetime.date
    ) -> PurchaseQuerySet:
        """Purchases the Supplier billed under this number in that financial year."""
        return self.alias(financial_year=financial_year("bill_date")).filter(
            supplier=supplier,
            bill_number=bill_number,
            financial_year=financial_year(
                models.Value(bill_date, output_field=models.DateField())
            ),
        )


class Purchase(models.Model):
    """A Supplier's bill recorded in billow. See CONTEXT.md."""

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchases"
    )
    bill_number = models.CharField(
        max_length=32, help_text="Exactly as the Supplier printed it."
    )
    bill_date = models.DateField(help_text="As printed on the bill.")
    received_date = models.DateField(
        help_text="The day the Goods arrived. Leave blank if it is the bill date."
    )

    # Copied from the Supplier when the Purchase is recorded, so correcting the
    # Supplier later leaves the tax on bills already on file as it was. Only
    # what decides tax is copied; see docs/adr/0007-invoices-snapshot-the-recipient.md.
    supplier_gstin = models.CharField(max_length=15, blank=True, verbose_name="GSTIN")
    supplier_state = state_field("The Supplier's state when the Purchase was recorded.")

    # Before tax only; one given off what is payable is not recorded. See
    # CONTEXT.md, Bill discount.
    bill_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="As printed, before tax. Leave blank if there is none.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    objects = PurchaseQuerySet.as_manager()

    class Meta:
        ordering = ("-received_date", "-pk")
        constraints = [
            models.UniqueConstraint(
                "supplier",
                "bill_number",
                financial_year("bill_date"),
                name="one_bill_number_per_supplier_per_financial_year",
                violation_error_message="This bill is already on file.",
            ),
            models.CheckConstraint(
                condition=models.Q(bill_discount__gte=0),
                name="bill_discount_is_not_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.bill_number} from {self.supplier}"

    def copy_supplier(self) -> None:
        self.supplier_gstin = self.supplier.gstin
        self.supplier_state = self.supplier.state

    def totals(self, business: Business | None = None) -> Totals:
        """What this Purchase comes to. Reads `lines` through any prefetch."""
        business = business or Business.load()
        return purchase_totals(
            [line.as_line() for line in self.lines.all()],
            supplier_state=self.supplier_state,
            supplier_gstin=self.supplier_gstin,
            business_state=business.state,
            business_registered=bool(business.is_gst_registered),
            bill_discount=self.bill_discount,
        )


class PurchaseLine(models.Model):
    """One line of a Purchase: Goods from the catalogue, as the Supplier billed them."""

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="purchase_lines"
    )
    # The unit and what it holds are copied rather than linked, so an Item's
    # units can be edited without the bills that used one changing under it.
    unit = models.CharField(max_length=3, choices=UNITS)
    stock_units_in_one = models.DecimalField(max_digits=18, decimal_places=6)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[validate_positive]
    )
    # Before tax, per unit billed. Zero is a free unit, as in "10 + 1 free".
    rate = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    gst_rate = models.DecimalField(
        max_digits=4, decimal_places=2, choices=GSTRate, verbose_name="GST rate"
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="discount",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="line_quantity_is_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(rate__gte=0), name="line_rate_is_not_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(discount_percent__range=(0, 100)),
                name="line_discount_is_a_percentage",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} {self.unit} {self.item}"

    def as_line(self) -> Line:
        return Line(
            quantity=self.quantity,
            rate=self.rate,
            gst_rate=self.gst_rate,
            stock_units_in_one=self.stock_units_in_one,
            discount_percent=self.discount_percent,
        )

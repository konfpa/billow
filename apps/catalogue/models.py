from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Cast, Substr
from simple_history.models import HistoricalRecords

from apps.tax.hsn_sac import validate_hsn, validate_sac
from apps.tax.rates import GSTRate
from apps.tax.units import REPORTED_UNDER, UNITS

ASSIGNED_CODE_PREFIX = "I-"
CODE_ATTEMPTS = 3

QUANTITY_STEP = Decimal("0.001")
PRICE_STEP = Decimal("0.01")


@dataclass(frozen=True)
class Quote:
    """What a quantity sold in one of an Item's units comes to."""

    stock_quantity: Decimal
    unit_price: Decimal | None
    # True when no price of the unit's own applies, and the stock unit's
    # price times the rate stands in for it.
    derived: bool


class Item(models.Model):
    """One thing the Business sells, described once. See CONTEXT.md.

    Each finish or size is its own Item; see
    docs/adr/0010-items-are-flat-no-variants.md.
    """

    # Every field is blankable, and what recording an Item demands is declared
    # here instead. The stock unit is not a column of the Item, but an Item
    # without one cannot be sold by quantity, so it is demanded all the same.
    # See docs/adr/0004-required-is-validation-not-schema.md.
    REQUIRED_TO_RECORD = ("name", "kind", "hsn_sac", "gst_rate", "stock_unit")

    class Kind(models.TextChoices):
        GOODS = "goods", "Goods"
        SERVICE = "service", "Service"

    name = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=7, blank=True, choices=Kind)
    # One field read by kind rather than two, so an Item can never carry both
    # an HSN code and a SAC.
    hsn_sac = models.CharField(
        max_length=8,
        blank=True,
        verbose_name="HSN/SAC code",
        help_text="An HSN code of 4, 6 or 8 digits for Goods, or a SAC for a Service.",
    )
    gst_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        choices=GSTRate,
        verbose_name="GST rate",
    )
    # Held to what a barcode label can print, so a code typed today can be
    # printed later without being retyped.
    code = models.CharField(
        max_length=32,
        blank=True,
        verbose_name="Item code",
        validators=[
            RegexValidator(
                r"^[A-Z0-9-]+$",
                "An Item code is capital letters, digits and hyphens.",
            )
        ],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("name",)
        constraints = [
            # Made structural so that two Operators saving at once, or a
            # `loaddata`, cannot leave one label meaning two Items.
            models.UniqueConstraint(fields=["code"], name="one_item_per_code"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        if self.code:
            super().save(*args, **kwargs)
            return

        # Two Operators recording at once read the same highest code, and the
        # constraint refuses the second; that one takes the next code instead.
        for attempt in range(CODE_ATTEMPTS):
            self.code = next_item_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == CODE_ATTEMPTS - 1:
                    raise
            else:
                return

    @property
    def stock_unit(self) -> ItemUnit | None:
        """The unit this Item is counted in. Read through `units` to use a prefetch."""
        return next((unit for unit in self.units.all() if unit.is_stock_unit), None)

    def quote(self, quantity: Decimal, unit: ItemUnit) -> Quote:
        """The stock quantity and unit price of `quantity` sold in `unit`.

        The only place unit arithmetic happens, so invoices and stock
        movements can never convert or price the same sale two ways.
        """
        if unit.item_id != self.pk:
            msg = f"{unit} is not a unit of {self}."
            raise ValueError(msg)

        stock_quantity = (quantity * unit.rate).quantize(QUANTITY_STEP, ROUND_HALF_UP)
        if unit.selling_price is not None or unit.is_stock_unit:
            return Quote(stock_quantity, unit.selling_price, derived=False)

        stock_price = self.stock_unit.selling_price
        if stock_price is None:
            return Quote(stock_quantity, None, derived=False)
        price = (stock_price * unit.rate).quantize(PRICE_STEP, ROUND_HALF_UP)
        return Quote(stock_quantity, price, derived=True)

    def above_mrp(self) -> list[tuple[ItemUnit, Decimal]]:
        """Each unit whose price, its own or worked out, is above its MRP.

        Warned about rather than refused, so a mistake is noticed without
        blocking the save.
        """
        above = []
        for unit in self.units.all():
            price = self.quote(Decimal(1), unit).unit_price
            if unit.mrp is not None and price is not None and price > unit.mrp:
                above.append((unit, price))
        return above

    def clean(self) -> None:
        super().clean()

        if self.code:
            holder = Item.objects.filter(code=self.code).exclude(pk=self.pk).first()
            if holder is not None:
                raise ValidationError(
                    {"code": f"{holder.name} already holds this Item code."}
                )

        if not self.hsn_sac or not self.kind:
            return

        validate = validate_hsn if self.kind == self.Kind.GOODS else validate_sac
        try:
            validate(self.hsn_sac)
        except ValidationError as error:
            raise ValidationError({"hsn_sac": error.messages}) from error


def next_item_code() -> str:
    """One past the highest `I-` code on file, which skips any already taken."""
    # An Operator may type an `I-` code too long for a bigint, and counting it
    # would fail every assignment after it; such a code can never be reached.
    highest = (
        Item.objects.filter(code__regex=rf"^{ASSIGNED_CODE_PREFIX}[0-9]{{1,18}}$")
        .annotate(
            number=Cast(
                Substr("code", len(ASSIGNED_CODE_PREFIX) + 1), models.BigIntegerField()
            )
        )
        .aggregate(models.Max("number"))["number__max"]
    )
    return f"{ASSIGNED_CODE_PREFIX}{(highest or 0) + 1:04d}"


def gst_quantity(quantity: Decimal, unit: str) -> tuple[Decimal, str]:
    """A quantity as a GST return reports it, and the GST unit code it is in.

    Only where GST reads a quantity is a unit without a code of its own
    converted; its value and tax are untouched, only the unit changes.
    """
    code, factor = REPORTED_UNDER.get(unit, (unit, Decimal(1)))
    return (quantity * factor).quantize(QUANTITY_STEP, ROUND_HALF_UP), code


def validate_positive(rate: Decimal) -> None:
    # A rate of zero or less would make stock vanish or run backwards.
    if rate <= 0:
        msg = "One unit holds more than zero of the stock unit."
        raise ValidationError(msg)


class ItemUnit(models.Model):
    """A unit an Item is bought or sold in, defined by its rate against the stock unit.

    The stock unit is the one row whose rate is 1. See
    docs/adr/0011-stock-is-the-sum-of-movements.md.
    """

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="units")
    code = models.CharField(max_length=3, choices=UNITS, verbose_name="unit")
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=1,
        validators=[validate_positive],
        help_text="How many of the stock unit one of this unit holds.",
    )
    is_stock_unit = models.BooleanField(default=False)
    # Including GST, as the price is quoted at the counter. Blank is an
    # answer: the price is then settled on the invoice.
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Including GST.",
    )
    mrp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="MRP",
    )

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # Checked at commit, so a stock unit and another unit can trade
            # places in one edit.
            models.UniqueConstraint(
                fields=["item", "code"],
                name="one_row_per_unit",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=["item"],
                condition=models.Q(is_stock_unit=True),
                name="one_stock_unit_per_item",
            ),
            models.CheckConstraint(
                condition=models.Q(rate__gt=0), name="unit_rate_is_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(is_stock_unit=True) | models.Q(rate=1),
                name="stock_unit_rate_is_one",
            ),
        ]

    def __str__(self) -> str:
        return self.code

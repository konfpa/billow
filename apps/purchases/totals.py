"""What a Purchase comes to: the one place its tax and cost are worked out.

Pure, so it is tested with plain figures, and so the detail page, the directory
and stock can never total the same bill two ways.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

RUPEE = Decimal(1)
PAISE = Decimal("0.01")
QUANTITY_STEP = Decimal("0.001")
HUNDRED = Decimal(100)
NOTHING = Decimal("0.00")
NOTHING_IN_STOCK = Decimal("0.000")


def paise(amount: Decimal) -> Decimal:
    return amount.quantize(PAISE, ROUND_HALF_UP)


@dataclass(frozen=True)
class Line:
    quantity: Decimal
    rate: Decimal
    gst_rate: Decimal
    # How many of the Item's stock unit one of the billed unit holds.
    stock_units_in_one: Decimal = Decimal(1)
    discount_percent: Decimal = Decimal(0)
    # Only Goods from the catalogue come into stock; a Service or a One-off
    # line such as freight is taxed and totalled but never counted.
    moves_stock: bool = True

    @property
    def gross(self) -> Decimal:
        return paise(self.quantity * self.rate)

    @property
    def discount(self) -> Decimal:
        return paise(self.gross * self.discount_percent / HUNDRED)

    @property
    def discounted(self) -> Decimal:
        """The line less its own discount, before any Bill discount."""
        return self.gross - self.discount


@dataclass(frozen=True)
class Tax:
    taxable_value: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal

    @property
    def tax(self) -> Decimal:
        return self.cgst + self.sgst + self.igst

    @property
    def amount(self) -> Decimal:
        return self.taxable_value + self.tax


@dataclass(frozen=True)
class LineTotals(Tax):
    gross: Decimal
    line_discount: Decimal
    bill_discount: Decimal
    moves_stock: bool
    stock_quantity: Decimal
    cost_per_stock_unit: Decimal

    @property
    def discounted(self) -> Decimal:
        return self.gross - self.line_discount


@dataclass(frozen=True)
class RateTotals(Tax):
    gst_rate: Decimal


@dataclass(frozen=True)
class Totals(Tax):
    bill_discount: Decimal
    lines: tuple[LineTotals, ...]
    by_rate: tuple[RateTotals, ...]
    round_off: Decimal = NOTHING

    @property
    def discounted(self) -> Decimal:
        """The lines less their own discounts, before the Bill discount."""
        return self.taxable_value + self.bill_discount

    @property
    def suggested_round_off(self) -> Decimal:
        """What brings the amount to a whole rupee, whatever Round-off was given."""
        return self.amount.quantize(RUPEE, ROUND_HALF_UP) - self.amount

    @property
    def grand_total(self) -> Decimal:
        return self.amount + self.round_off


def purchase_totals(  # noqa: PLR0913
    lines: tuple[Line, ...] | list[Line],
    *,
    supplier_state: str,
    supplier_gstin: str,
    business_state: str,
    business_registered: bool,
    bill_discount: Decimal = NOTHING,
    round_off: Decimal = NOTHING,
) -> Totals:
    """Each line's taxable value, tax and cost, the tax by GST rate, and the total.

    A line's taxable value is its gross less its own discount and its share of
    the Bill discount, which is spread in proportion to what each line comes
    to after its own discount.

    Tax is CGST plus SGST when the Supplier is in the Business's state and IGST
    otherwise, and nothing from a Supplier holding no GSTIN, who cannot charge
    it. It is rounded to paise on each line, as bills print it.
    """
    charges_tax = bool(supplier_gstin)
    within_state = supplier_state == business_state

    shares = _spread(bill_discount, [line.discounted for line in lines])

    totalled = []
    for line, share in zip(lines, shares, strict=True):
        taxable_value = line.discounted - share
        cgst = sgst = igst = NOTHING
        if charges_tax and within_state:
            cgst = sgst = paise(taxable_value * line.gst_rate / 2 / HUNDRED)
        elif charges_tax:
            igst = paise(taxable_value * line.gst_rate / HUNDRED)

        # Tax a registered Business claims back is not part of what the Goods
        # cost it; one that is not registered bears it.
        cost = taxable_value
        if not business_registered:
            cost += cgst + sgst + igst
        stock_quantity = NOTHING_IN_STOCK
        if line.moves_stock:
            stock_quantity = (line.quantity * line.stock_units_in_one).quantize(
                QUANTITY_STEP, ROUND_HALF_UP
            )

        totalled.append(
            LineTotals(
                gross=line.gross,
                line_discount=line.discount,
                bill_discount=share,
                moves_stock=line.moves_stock,
                taxable_value=taxable_value,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                stock_quantity=stock_quantity,
                cost_per_stock_unit=paise(cost / stock_quantity)
                if stock_quantity
                else NOTHING,
            )
        )

    at_rate = defaultdict(list)
    for line, line_totals in zip(lines, totalled, strict=True):
        at_rate[line.gst_rate].append(line_totals)
    by_rate = tuple(
        RateTotals(gst_rate=rate, **_summed(at_rate[rate])) for rate in sorted(at_rate)
    )

    return Totals(
        bill_discount=sum(shares, NOTHING),
        lines=tuple(totalled),
        by_rate=by_rate,
        round_off=round_off,
        **_summed(totalled),
    )


def _spread(amount: Decimal, values: list[Decimal]) -> list[Decimal]:
    """`amount` shared in proportion to `values`, in paise that add up to it.

    Each share is the rounded running total less the one before, so the paise
    lost rounding one share are made up in the next rather than lost.
    """
    whole = sum(values, NOTHING)
    if not whole:
        return [NOTHING] * len(values)

    shares = []
    running = shared = NOTHING
    for value in values:
        running += value
        upto = paise(amount * running / whole)
        shares.append(upto - shared)
        shared = upto
    return shares


def _summed(taxes: list[Tax]) -> dict[str, Decimal]:
    return {
        "taxable_value": sum((tax.taxable_value for tax in taxes), NOTHING),
        "cgst": sum((tax.cgst for tax in taxes), NOTHING),
        "sgst": sum((tax.sgst for tax in taxes), NOTHING),
        "igst": sum((tax.igst for tax in taxes), NOTHING),
    }

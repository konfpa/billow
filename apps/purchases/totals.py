"""What a Purchase comes to: the one place its tax and cost are worked out.

Pure, so it is tested with plain figures, and so the detail page, the directory
and stock can never total the same bill two ways.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PAISE = Decimal("0.01")
QUANTITY_STEP = Decimal("0.001")
HUNDRED = Decimal(100)
NOTHING = Decimal("0.00")


def paise(amount: Decimal) -> Decimal:
    return amount.quantize(PAISE, ROUND_HALF_UP)


@dataclass(frozen=True)
class Line:
    quantity: Decimal
    rate: Decimal
    gst_rate: Decimal
    # How many of the Item's stock unit one of the billed unit holds.
    stock_units_in_one: Decimal = Decimal(1)


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
    stock_quantity: Decimal
    cost_per_stock_unit: Decimal


@dataclass(frozen=True)
class RateTotals(Tax):
    gst_rate: Decimal


@dataclass(frozen=True)
class Totals(Tax):
    lines: tuple[LineTotals, ...]
    by_rate: tuple[RateTotals, ...]

    @property
    def grand_total(self) -> Decimal:
        return self.amount


def purchase_totals(
    lines: tuple[Line, ...] | list[Line],
    *,
    supplier_state: str,
    supplier_gstin: str,
    business_state: str,
    business_registered: bool,
) -> Totals:
    """Each line's taxable value, tax and cost, the tax by GST rate, and the total.

    Tax is CGST plus SGST when the Supplier is in the Business's state and IGST
    otherwise, and nothing from a Supplier holding no GSTIN, who cannot charge
    it. It is rounded to paise on each line, as bills print it.
    """
    charges_tax = bool(supplier_gstin)
    within_state = supplier_state == business_state

    totalled = []
    for line in lines:
        taxable_value = paise(line.quantity * line.rate)
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
        stock_quantity = (line.quantity * line.stock_units_in_one).quantize(
            QUANTITY_STEP, ROUND_HALF_UP
        )

        totalled.append(
            LineTotals(
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

    return Totals(lines=tuple(totalled), by_rate=by_rate, **_summed(totalled))


def _summed(taxes: list[Tax]) -> dict[str, Decimal]:
    return {
        "taxable_value": sum((tax.taxable_value for tax in taxes), NOTHING),
        "cgst": sum((tax.cgst for tax in taxes), NOTHING),
        "sgst": sum((tax.sgst for tax in taxes), NOTHING),
        "igst": sum((tax.igst for tax in taxes), NOTHING),
    }

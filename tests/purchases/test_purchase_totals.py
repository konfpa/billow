from decimal import Decimal

from apps.purchases.totals import Line, purchase_totals
from apps.tax.states import State

MAHARASHTRA_GSTIN = "27AAACM1234K1ZN"
KARNATAKA_GSTIN = "29AAACM1234K1ZJ"


def totals(
    *lines,
    supplier_state=State.MAHARASHTRA,
    supplier_gstin=MAHARASHTRA_GSTIN,
    business_registered=True,
):
    return purchase_totals(
        lines,
        supplier_state=supplier_state,
        supplier_gstin=supplier_gstin,
        business_state=State.MAHARASHTRA,
        business_registered=business_registered,
    )


def line(quantity="1", rate="100", gst_rate="18.00", stock_units_in_one="1"):
    return Line(
        quantity=Decimal(quantity),
        rate=Decimal(rate),
        gst_rate=Decimal(gst_rate),
        stock_units_in_one=Decimal(stock_units_in_one),
    )


def test_a_supplier_in_the_business_state_charges_cgst_and_sgst():
    result = totals(line(quantity="3", rate="100"))

    [taxed] = result.lines
    assert taxed.taxable_value == Decimal("300.00")
    assert taxed.cgst == Decimal("27.00")
    assert taxed.sgst == Decimal("27.00")
    assert taxed.igst == Decimal("0.00")
    assert result.grand_total == Decimal("354.00")


def test_a_supplier_in_another_state_charges_igst():
    result = totals(
        line(quantity="3", rate="100"),
        supplier_state=State.KARNATAKA,
        supplier_gstin=KARNATAKA_GSTIN,
    )

    [taxed] = result.lines
    assert taxed.cgst == Decimal("0.00")
    assert taxed.sgst == Decimal("0.00")
    assert taxed.igst == Decimal("54.00")
    assert result.grand_total == Decimal("354.00")


def test_an_unregistered_supplier_charges_no_tax():
    result = totals(line(quantity="3", rate="100"), supplier_gstin="")

    [untaxed] = result.lines
    assert untaxed.tax == Decimal("0.00")
    assert result.tax == Decimal("0.00")
    assert result.grand_total == Decimal("300.00")


def test_an_unregistered_supplier_in_another_state_charges_no_igst_either():
    result = totals(line(), supplier_state=State.KARNATAKA, supplier_gstin="")

    assert result.igst == Decimal("0.00")
    assert result.grand_total == Decimal("100.00")


def test_tax_is_rounded_to_paise_on_each_line():
    # 18% of 10.05 is 1.809: 0.9045 each way, rounded half up per line.
    result = totals(line(rate="10.05"), line(rate="10.05"))

    assert [taxed.cgst for taxed in result.lines] == [Decimal("0.90")] * 2
    assert result.cgst == Decimal("1.80")
    assert result.sgst == Decimal("1.80")


def test_a_line_is_its_quantity_at_its_rate_rounded_to_paise():
    result = totals(line(quantity="2.5", rate="33.33"))

    assert result.lines[0].taxable_value == Decimal("83.33")


def test_a_line_billed_in_another_unit_counts_in_the_stock_unit():
    # Two pieces of 20 ft pipe at ₹240 a piece.
    result = totals(line(quantity="2", rate="240", stock_units_in_one="20"))

    [pipe] = result.lines
    assert pipe.stock_quantity == Decimal("40.000")
    assert pipe.cost_per_stock_unit == Decimal("12.00")


def test_a_registered_business_leaves_tax_out_of_cost():
    result = totals(line(quantity="4", rate="100"))

    assert result.lines[0].cost_per_stock_unit == Decimal("100.00")


def test_an_unregistered_business_bears_the_tax_in_its_cost():
    result = totals(line(quantity="4", rate="100"), business_registered=False)

    assert result.lines[0].cost_per_stock_unit == Decimal("118.00")


def test_a_free_line_comes_in_at_no_cost_and_no_tax():
    # "10 + 1 free": the free one is its own line at ₹0.
    result = totals(line(quantity="10", rate="50"), line(quantity="1", rate="0"))

    free = result.lines[1]
    assert free.taxable_value == Decimal("0.00")
    assert free.tax == Decimal("0.00")
    assert free.stock_quantity == Decimal("1.000")
    assert free.cost_per_stock_unit == Decimal("0.00")
    assert result.grand_total == Decimal("590.00")


def test_taxable_value_and_tax_are_summed_by_gst_rate():
    result = totals(
        line(quantity="2", rate="100", gst_rate="18.00"),
        line(quantity="1", rate="200", gst_rate="5.00"),
        line(quantity="1", rate="50", gst_rate="18.00"),
    )

    assert [
        (group.gst_rate, group.taxable_value, group.cgst, group.sgst, group.igst)
        for group in result.by_rate
    ] == [
        (
            Decimal("5.00"),
            Decimal("200.00"),
            Decimal("5.00"),
            Decimal("5.00"),
            Decimal("0.00"),
        ),
        (
            Decimal("18.00"),
            Decimal("250.00"),
            Decimal("22.50"),
            Decimal("22.50"),
            Decimal("0.00"),
        ),
    ]
    assert result.taxable_value == Decimal("450.00")
    assert result.tax == Decimal("55.00")
    assert result.grand_total == Decimal("505.00")


def test_no_lines_come_to_nothing():
    result = totals()

    assert result.by_rate == ()
    assert result.grand_total == Decimal("0.00")

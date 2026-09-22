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
    bill_discount="0",
    round_off="0",
):
    return purchase_totals(
        lines,
        bill_discount=Decimal(bill_discount),
        round_off=Decimal(round_off),
        supplier_state=supplier_state,
        supplier_gstin=supplier_gstin,
        business_state=State.MAHARASHTRA,
        business_registered=business_registered,
    )


def line(  # noqa: PLR0913
    quantity="1",
    rate="100",
    gst_rate="18.00",
    stock_units_in_one="1",
    discount="0",
    *,
    moves_stock=True,
):
    return Line(
        quantity=Decimal(quantity),
        rate=Decimal(rate),
        gst_rate=Decimal(gst_rate),
        stock_units_in_one=Decimal(stock_units_in_one),
        discount_percent=Decimal(discount),
        moves_stock=moves_stock,
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


def test_a_line_discount_comes_off_the_line_before_tax():
    result = totals(line(quantity="4", rate="250", discount="10"))

    [discounted] = result.lines
    assert discounted.gross == Decimal("1000.00")
    assert discounted.line_discount == Decimal("100.00")
    assert discounted.taxable_value == Decimal("900.00")
    assert discounted.cgst == Decimal("81.00")
    assert result.grand_total == Decimal("1062.00")


def test_a_line_discount_is_rounded_to_paise():
    # 7.5% of 33.33 is 2.49975.
    result = totals(line(rate="33.33", discount="7.5"))

    assert result.lines[0].line_discount == Decimal("2.50")
    assert result.lines[0].taxable_value == Decimal("30.83")


def test_the_bill_discount_is_spread_by_taxable_value_across_gst_rates():
    # ₹100 off lines worth ₹600 at 18% and ₹400 at 5% after a line discount.
    result = totals(
        line(quantity="1", rate="600", gst_rate="18.00"),
        line(quantity="1", rate="500", gst_rate="5.00", discount="20"),
        bill_discount="100",
    )

    eighteen, five = result.lines
    assert eighteen.bill_discount == Decimal("60.00")
    assert eighteen.taxable_value == Decimal("540.00")
    assert eighteen.cgst == Decimal("48.60")
    assert five.bill_discount == Decimal("40.00")
    assert five.taxable_value == Decimal("360.00")
    assert five.cgst == Decimal("9.00")
    assert [(group.gst_rate, group.taxable_value) for group in result.by_rate] == [
        (Decimal("5.00"), Decimal("360.00")),
        (Decimal("18.00"), Decimal("540.00")),
    ]
    assert result.bill_discount == Decimal("100.00")
    assert result.taxable_value == Decimal("900.00")
    assert result.tax == Decimal("115.20")
    assert result.grand_total == Decimal("1015.20")


def test_the_bill_discount_comes_off_before_igst():
    result = totals(
        line(quantity="1", rate="600", gst_rate="18.00"),
        line(quantity="1", rate="400", gst_rate="5.00"),
        bill_discount="100",
        supplier_state=State.KARNATAKA,
        supplier_gstin=KARNATAKA_GSTIN,
    )

    assert [taxed.igst for taxed in result.lines] == [
        Decimal("97.20"),
        Decimal("18.00"),
    ]
    assert result.grand_total == Decimal("1015.20")


def test_the_bill_discount_shares_add_up_to_it_exactly():
    # A third of ₹10 each is 3.333…; rounded alone, the shares would miss a paisa.
    result = totals(line(), line(), line(), bill_discount="10")

    shares = [taxed.bill_discount for taxed in result.lines]
    assert sum(shares) == Decimal("10.00")
    assert all(share in {Decimal("3.33"), Decimal("3.34")} for share in shares)


def test_a_free_line_bears_none_of_the_bill_discount():
    result = totals(line(rate="100"), line(rate="0"), bill_discount="5")

    assert [taxed.bill_discount for taxed in result.lines] == [
        Decimal("5.00"),
        Decimal("0.00"),
    ]


def test_the_bill_discount_lowers_cost():
    result = totals(line(quantity="4", rate="100"), bill_discount="40")

    assert result.lines[0].cost_per_stock_unit == Decimal("90.00")


def test_the_suggested_round_off_brings_the_total_to_a_whole_rupee():
    result = totals(line(quantity="1", rate="860"))

    assert result.amount == Decimal("1014.80")
    assert result.suggested_round_off == Decimal("0.20")


def test_the_suggested_round_off_takes_paise_off_below_half_a_rupee():
    result = totals(line(quantity="1", rate="860.35"))

    assert result.amount == Decimal("1015.21")
    assert result.suggested_round_off == Decimal("-0.21")


def test_half_a_rupee_rounds_up():
    result = totals(line(rate="50.50", gst_rate="0"))

    assert result.amount == Decimal("50.50")
    assert result.suggested_round_off == Decimal("0.50")


def test_a_whole_rupee_total_needs_no_round_off():
    assert totals(line()).suggested_round_off == Decimal("0.00")


def test_the_round_off_is_added_to_the_grand_total():
    result = totals(line(quantity="1", rate="860"), round_off="-0.80")

    assert result.round_off == Decimal("-0.80")
    assert result.grand_total == Decimal("1014.00")


def test_the_suggestion_does_not_depend_on_the_round_off_given():
    result = totals(line(quantity="1", rate="860"), round_off="-0.80")

    assert result.suggested_round_off == Decimal("0.20")


def test_a_goods_line_moves_stock():
    assert totals(line()).lines[0].moves_stock


def test_a_line_moving_no_stock_is_taxed_and_totalled_but_not_costed():
    # Goods, and freight billed as a One-off line.
    result = totals(
        line(quantity="10", rate="100"),
        line(quantity="1", rate="200", gst_rate="5.00", moves_stock=False),
    )

    goods, freight = result.lines
    assert not freight.moves_stock
    assert freight.taxable_value == Decimal("200.00")
    assert freight.cgst == Decimal("5.00")
    assert freight.stock_quantity == Decimal("0.000")
    assert freight.cost_per_stock_unit == Decimal("0.00")
    assert goods.cost_per_stock_unit == Decimal("100.00")
    assert [rate.gst_rate for rate in result.by_rate] == [
        Decimal("5.00"),
        Decimal("18.00"),
    ]
    assert result.grand_total == Decimal("1390.00")


def test_a_line_moving_no_stock_bears_its_share_of_the_bill_discount():
    result = totals(
        line(quantity="1", rate="300"),
        line(quantity="1", rate="100", moves_stock=False),
        bill_discount="40",
    )

    assert result.lines[1].taxable_value == Decimal("90.00")

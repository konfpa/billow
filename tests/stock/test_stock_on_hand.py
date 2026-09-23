import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.purchases.models import Purchase
from apps.stock.models import StockMovement
from tests.conftest import PASSWORD, role
from tests.purchases.conftest import goods, line
from tests.stock.conftest import buy

User = get_user_model()


def detail(client, item):
    return client.get(reverse("item_detail", args=[item.pk]))


def movements(client, item):
    return list(detail(client, item).context["movements"])


def stock_on_hand(client, item):
    return detail(client, item).context["item"].stock_on_hand


@pytest.mark.django_db
def test_a_purchase_of_goods_brings_them_into_stock(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow, quantity="10", rate="100.00"))

    page = detail(client, elbow).content.decode()

    purchase = Purchase.objects.get()
    assert "Stock on hand" in page
    assert "10 NOS" in page
    assert "18 Sep 2026" in page
    assert "₹100.00" in page
    assert reverse("purchase_detail", args=[purchase.pk]) in page


@pytest.mark.django_db
def test_a_line_billed_in_another_unit_is_counted_in_the_stock_unit(
    client, signed_in, supplier, pipe
):
    # Two bundles of 20 at ₹400 a bundle, taxable ₹800 over 40 pipes.
    buy(client, supplier, line(pipe, unit="BDL", quantity="2", rate="400.00"))

    page = detail(client, pipe).content.decode()

    assert "40 NOS" in page
    assert "₹20.00" in page


@pytest.mark.django_db
def test_a_registered_business_costs_goods_without_the_tax_it_claims_back(
    client, signed_in, supplier, elbow
):
    buy(client, supplier, line(elbow, quantity="4", rate="250.00"))

    [movement] = movements(client, elbow)

    assert str(movement.cost_per_stock_unit) == "250.00"


@pytest.mark.django_db
def test_a_business_not_registered_costs_goods_with_the_tax_it_bears(
    client, signed_in, business, supplier, elbow
):
    business.is_gst_registered = False
    business.gstin = ""
    business.save()

    buy(client, supplier, line(elbow, quantity="4", rate="250.00"))

    [movement] = movements(client, elbow)

    assert str(movement.cost_per_stock_unit) == "295.00"


@pytest.mark.django_db
def test_the_bill_discount_lowers_the_cost(client, signed_in, supplier, elbow):
    buy(
        client,
        supplier,
        line(elbow, quantity="10", rate="100.00"),
        bill_discount="100.00",
    )

    [movement] = movements(client, elbow)

    assert str(movement.cost_per_stock_unit) == "90.00"


@pytest.mark.django_db
def test_services_and_one_off_lines_bring_nothing_into_stock(
    client, signed_in, supplier, elbow
):
    fitting = goods("Fitting", "FIT", kind="service")

    buy(
        client,
        supplier,
        line(elbow, quantity="10", rate="100.00"),
        line(fitting, quantity="1", rate="500.00"),
        {
            "name": "Freight",
            "hsn_sac": "996511",
            "gst_rate": "18.00",
            "quantity": "1",
            "rate": "200.00",
        },
    )

    assert str(stock_on_hand(client, elbow)) == "10.000"
    assert "Stock on hand" not in detail(client, fitting).content.decode()


@pytest.mark.django_db
def test_stock_adds_up_every_purchase(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow, quantity="10"))
    buy(client, supplier, line(elbow, quantity="5"), bill_number="MP/2026-27/0413")

    assert str(stock_on_hand(client, elbow)) == "15.000"
    assert len(movements(client, elbow)) == 2


@pytest.mark.django_db
def test_movements_are_dated_on_the_received_date(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow), received_date="2026-09-21")

    [movement] = movements(client, elbow)

    assert movement.date == datetime.date(2026, 9, 21)


@pytest.mark.django_db
def test_goods_received_before_the_stock_start_date_are_not_counted(
    client, signed_in, supplier, elbow
):
    buy(
        client,
        supplier,
        line(elbow, quantity="7"),
        bill_date="2026-03-28",
        received_date="2026-03-30",
    )
    buy(client, supplier, line(elbow, quantity="10"))

    assert str(stock_on_hand(client, elbow)) == "10.000"
    assert len(movements(client, elbow)) == 1


@pytest.mark.django_db
def test_no_stock_is_shown_until_the_stock_start_date_is_set(
    client, signed_in, business, supplier, elbow
):
    business.stock_start_date = None
    business.save()

    buy(client, supplier, line(elbow, quantity="10"))

    page = detail(client, elbow).content.decode()
    assert "Stock on hand" not in page
    assert "No stock is counted yet" in page


@pytest.mark.django_db
def test_moving_the_stock_start_date_recounts_what_is_already_recorded(
    client, signed_in, business, supplier, elbow
):
    business.stock_start_date = None
    business.save()
    buy(
        client,
        supplier,
        line(elbow, quantity="7"),
        bill_date="2026-03-28",
        received_date="2026-03-30",
    )
    buy(client, supplier, line(elbow, quantity="10"))

    business.stock_start_date = datetime.date(2026, 4, 1)
    business.save()
    assert str(stock_on_hand(client, elbow)) == "10.000"

    business.stock_start_date = datetime.date(2026, 3, 1)
    business.save()
    assert str(stock_on_hand(client, elbow)) == "17.000"


@pytest.mark.django_db
def test_stock_on_hand_may_go_negative(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow, quantity="10"))
    # As a sale will record goods going out, once sales move stock.
    StockMovement.objects.create(
        item=elbow,
        date=datetime.date(2026, 9, 20),
        quantity=Decimal(-13),
        cost_per_stock_unit=Decimal("100.00"),
    )

    page = detail(client, elbow).content.decode()

    assert "-3 NOS" in page


@pytest.mark.django_db
def test_anyone_who_may_view_the_item_sees_its_stock(client, business, supplier, elbow):
    buyer = User.objects.create_user(
        email="neha@example.com", name="Neha Joshi", password=PASSWORD
    )
    buyer.groups.add(role("Purchasing", "purchases.add_purchase"))
    client.force_login(buyer)
    buy(client, supplier, line(elbow, quantity="10"))

    looker = User.objects.create_user(
        email="ravi@example.com", name="Ravi Kumar", password=PASSWORD
    )
    looker.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(looker)
    page = detail(client, elbow).content.decode()

    purchase = Purchase.objects.get()
    assert "10 NOS" in page
    assert "MP/2026-27/0412" in page
    assert reverse("purchase_detail", args=[purchase.pk]) not in page

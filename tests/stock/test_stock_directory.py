from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tests.purchases.conftest import goods, line
from tests.stock.conftest import buy

DIRECTORY = reverse("item_directory")


def stock_column(client):
    """Each Item's name and what the directory says it has in stock."""
    items = client.get(DIRECTORY).context["items"]
    return {item.name: item.stock_on_hand for item in items}


@pytest.mark.django_db
def test_the_directory_shows_the_stock_of_goods(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow, quantity="10"))

    page = client.get(DIRECTORY).content.decode()

    assert "Stock on hand" in page
    assert "10 NOS" in page


@pytest.mark.django_db
def test_goods_with_nothing_bought_show_none_in_stock(client, signed_in, elbow):
    assert stock_column(client)["CPVC elbow ¾ inch"] == Decimal(0)


@pytest.mark.django_db
def test_a_service_shows_no_stock(client, signed_in, business):
    goods("Fitting", "FIT", kind="service")

    page = client.get(DIRECTORY).content.decode()

    assert stock_column(client) == {"Fitting": None}
    assert "0 NOS" not in page


@pytest.mark.django_db
def test_the_directory_counts_only_from_the_stock_start_date(
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

    assert stock_column(client)["CPVC elbow ¾ inch"] == Decimal(10)


@pytest.mark.django_db
def test_the_directory_shows_no_stock_until_the_stock_start_date_is_set(
    client, signed_in, business, supplier, elbow
):
    business.stock_start_date = None
    business.save()
    buy(client, supplier, line(elbow, quantity="10"))

    page = client.get(DIRECTORY).content.decode()

    assert "Stock on hand" not in page
    assert "10 NOS" not in page


@pytest.mark.django_db
def test_the_stock_column_takes_no_query_per_row(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow))
    with CaptureQueriesContext(connection) as one_item:
        client.get(DIRECTORY)

    for number in range(3):
        tee = goods(f"Tee {number}", f"TEE-{number}")
        buy(client, supplier, line(tee), bill_number=f"MP/2026-27/05{number}")
    with CaptureQueriesContext(connection) as four_items:
        client.get(DIRECTORY)

    assert len(four_items.captured_queries) == len(one_item.captured_queries)

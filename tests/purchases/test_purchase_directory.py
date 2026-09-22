import datetime

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase, PurchaseLine
from tests.conftest import role

DIRECTORY = reverse("purchase_directory")


def bill(supplier, item, number, received, rate="100"):
    purchase = Purchase.objects.create(
        supplier=supplier,
        bill_number=number,
        bill_date=received,
        received_date=received,
    )
    purchase.copy_supplier()
    purchase.save()
    PurchaseLine.objects.create(
        purchase=purchase,
        item=item,
        unit="NOS",
        stock_units_in_one=1,
        quantity=1,
        rate=rate,
        gst_rate="18.00",
    )
    return purchase


@pytest.mark.django_db
def test_nothing_recorded_says_so(client, signed_in):
    page = client.get(DIRECTORY).content.decode()

    assert "No Purchases recorded yet" in page


@pytest.mark.django_db
def test_purchases_are_listed_newest_received_first(client, signed_in, supplier, elbow):
    bill(supplier, elbow, "A-1", datetime.date(2026, 9, 1))
    bill(supplier, elbow, "A-3", datetime.date(2026, 9, 20))
    bill(supplier, elbow, "A-2", datetime.date(2026, 9, 10))

    page = client.get(DIRECTORY).content.decode()

    assert page.index("A-3") < page.index("A-2") < page.index("A-1")


@pytest.mark.django_db
def test_each_row_shows_supplier_bill_date_and_grand_total(
    client, signed_in, supplier, elbow
):
    purchase = bill(supplier, elbow, "A-1", datetime.date(2026, 9, 1), rate="1000")

    page = client.get(DIRECTORY).content.decode()

    assert "Mehta Pipes" in page
    assert "1 Sep 2026" in page
    assert "₹1,180.00" in page
    assert reverse("purchase_detail", args=[purchase.pk]) in page


@pytest.mark.django_db
def test_new_purchase_is_offered_only_with_add_purchase(client, business, powerless):
    powerless.groups.add(role("Reader", "purchases.view_purchase"))
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert reverse("record_purchase") not in page

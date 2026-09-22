import datetime

import pytest
from django.urls import reverse

from tests.conftest import role
from tests.purchases.conftest import bill


def detail(supplier):
    return reverse("supplier_detail", args=[supplier.pk])


@pytest.fixture
def looker(client, business, powerless):
    """An Operator who may see Suppliers, and is given more as a test needs."""
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)
    return powerless


@pytest.fixture
def reader(looker):
    looker.groups.add(role("Reader", "purchases.view_purchase"))
    return looker


@pytest.mark.django_db
def test_supplier_detail_lists_their_purchases_newest_received_first(
    client, reader, supplier, karnataka_supplier, elbow
):
    older = bill(supplier, elbow, "MP/0412", datetime.date(2026, 8, 20), rate="1000")
    # Billed first, but received last.
    newer = bill(supplier, elbow, "MP/0519", datetime.date(2026, 9, 12))
    newer.bill_date = datetime.date(2026, 8, 1)
    newer.save()
    bill(karnataka_supplier, elbow, "KF-77", datetime.date(2026, 9, 3))

    page = client.get(detail(supplier)).content.decode()

    assert page.index("MP/0519") < page.index("MP/0412")
    assert "KF-77" not in page
    assert reverse("purchase_detail", args=[older.pk]) in page
    assert "₹1,180.00" in page


@pytest.mark.django_db
def test_supplier_detail_links_to_their_purchases_in_the_directory(
    client, reader, supplier, elbow
):
    bill(supplier, elbow, "MP/0412", datetime.date(2026, 8, 20))

    page = client.get(detail(supplier)).content.decode()

    assert f"{reverse('purchase_directory')}?supplier={supplier.pk}" in page


@pytest.mark.django_db
def test_a_supplier_with_no_purchases_says_so(client, reader, supplier):
    page = client.get(detail(supplier)).content.decode()

    assert "No Purchases from Mehta Pipes yet" in page


@pytest.mark.django_db
def test_purchases_are_shown_only_with_view_purchase(client, looker, supplier, elbow):
    bill(supplier, elbow, "MP/0412", datetime.date(2026, 8, 20))

    page = client.get(detail(supplier)).content.decode()

    assert "MP/0412" not in page
    assert 'id="supplier-purchases-h"' not in page

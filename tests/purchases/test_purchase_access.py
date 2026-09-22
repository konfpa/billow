import datetime

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase, PurchaseLine
from tests.conftest import role
from tests.purchases.conftest import line, submitted

DIRECTORY = reverse("purchase_directory")
RECORD = reverse("record_purchase")


@pytest.fixture
def purchase(supplier, elbow):
    bill = Purchase.objects.create(
        supplier=supplier,
        bill_number="A-1",
        bill_date=datetime.date(2026, 9, 1),
        received_date=datetime.date(2026, 9, 1),
    )
    PurchaseLine.objects.create(
        purchase=bill,
        item=elbow,
        unit="NOS",
        stock_units_in_one=1,
        quantity=1,
        rate=100,
        gst_rate="18.00",
    )
    return bill


def reading(purchase):
    return [DIRECTORY, reverse("purchase_detail", args=[purchase.pk])]


@pytest.mark.django_db
def test_without_view_purchase_reading_purchases_is_refused(
    client, business, powerless, purchase
):
    powerless.groups.add(role("Recorder", "purchases.add_purchase"))
    client.force_login(powerless)

    for url in reading(purchase):
        response = client.get(url)

        assert response.status_code == 403, url
        assert "Can view purchase" in response.content.decode()


@pytest.mark.django_db
def test_view_purchase_opens_the_directory_and_detail(
    client, business, powerless, purchase
):
    powerless.groups.add(role("Reader", "purchases.view_purchase"))
    client.force_login(powerless)

    for url in reading(purchase):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_without_add_purchase_recording_is_refused(
    client, business, powerless, supplier, elbow
):
    powerless.groups.add(role("Reader", "purchases.view_purchase"))
    client.force_login(powerless)

    page = client.get(RECORD)
    posted = client.post(RECORD, submitted(supplier, line(elbow)))

    assert page.status_code == 403
    assert "Can add purchase" in page.content.decode()
    assert posted.status_code == 403
    assert not Purchase.objects.exists()


def purchases_link(page):
    """The opening tag of the sidebar's Purchases link."""
    start = page.index('data-tip="Purchases"')
    return page[start : page.index(">", start)]


@pytest.mark.django_db
def test_the_sidebar_offers_purchases_only_with_view_purchase(
    client, business, powerless
):
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)

    assert 'data-tip="Purchases"' not in client.get(reverse("home")).content.decode()

    powerless.groups.add(role("Reader", "purchases.view_purchase"))
    page = client.get(reverse("home")).content.decode()

    assert page.index('data-tip="Suppliers"') < page.index('data-tip="Purchases"')


@pytest.mark.django_db
def test_the_purchases_link_is_current_on_every_purchase_page(
    client, business, signed_in, purchase
):
    for url in (*reading(purchase), RECORD):
        page = client.get(url).content.decode()

        assert 'aria-current="page"' in purchases_link(page), url


@pytest.mark.django_db
def test_the_purchases_link_is_not_current_elsewhere(client, signed_in):
    page = client.get(reverse("home")).content.decode()

    assert 'aria-current="page"' not in purchases_link(page)


@pytest.mark.django_db
def test_home_offers_purchases_only_with_view_purchase(client, business, powerless):
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)

    assert 'id="home-purchases-h"' not in client.get(reverse("home")).content.decode()

    powerless.groups.add(role("Reader", "purchases.view_purchase"))
    page = client.get(reverse("home")).content.decode()

    assert 'id="home-purchases-h"' in page
    assert DIRECTORY in page

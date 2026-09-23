import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.conftest import role
from tests.purchases.conftest import as_it_stands, line
from tests.stock.conftest import buy


@pytest.fixture
def signed_in(signed_in):
    """The storekeeper, trusted to correct and delete Purchases too."""
    signed_in.groups.add(
        role(
            "Purchase corrections",
            "purchases.change_purchase",
            "purchases.delete_purchase",
        )
    )
    return signed_in


def correct(client, purchase, **changes):
    response = client.post(
        reverse("edit_purchase", args=[purchase.pk]),
        as_it_stands(purchase, **changes),
    )
    assert response.status_code == 302, response.context["form"].errors


def stock_on_hand(client, item):
    return (
        client.get(reverse("item_detail", args=[item.pk])).context["item"].stock_on_hand
    )


def movements(client, item):
    page = client.get(reverse("item_detail", args=[item.pk]))
    return [
        (movement.date, movement.quantity) for movement in page.context["movements"]
    ]


@pytest.mark.django_db
def test_a_corrected_quantity_corrects_stock_on_hand(
    client, signed_in, supplier, elbow
):
    buy(client, supplier, line(elbow, quantity="10"))

    correct(
        client,
        Purchase.objects.get(),
        **{"lines-0-quantity": "12"},
        billed_total="1416.00",
    )

    assert stock_on_hand(client, elbow) == Decimal(12)


@pytest.mark.django_db
def test_a_corrected_received_date_moves_the_movement(
    client, signed_in, supplier, elbow
):
    buy(client, supplier, line(elbow, quantity="10"))

    correct(client, Purchase.objects.get(), received_date="2026-09-20")

    assert movements(client, elbow) == [(datetime.date(2026, 9, 20), Decimal(10))]


@pytest.mark.django_db
def test_a_line_moved_to_another_item_moves_its_stock_with_it(
    client, signed_in, supplier, elbow, pipe
):
    buy(client, supplier, line(elbow, quantity="10"))

    correct(
        client,
        Purchase.objects.get(),
        **{"lines-0-item": str(pipe.pk), "lines-0-gst_rate": ""},
        billed_total="1050.00",
    )

    assert stock_on_hand(client, elbow) == 0
    assert stock_on_hand(client, pipe) == Decimal(10)


@pytest.mark.django_db
def test_a_removed_line_takes_its_stock_with_it(
    client, signed_in, supplier, elbow, pipe
):
    buy(client, supplier, line(elbow, quantity="10"), line(pipe, quantity="3"))

    correct(
        client,
        Purchase.objects.get(),
        **{"lines-1-DELETE": "on"},
        billed_total="1180.00",
    )

    assert stock_on_hand(client, elbow) == Decimal(10)
    assert stock_on_hand(client, pipe) == 0


@pytest.mark.django_db
def test_a_deleted_purchase_takes_its_stock_with_it(client, signed_in, supplier, elbow):
    buy(client, supplier, line(elbow, quantity="10"))
    buy(client, supplier, line(elbow, quantity="4"), bill_number="MP/0413")

    client.post(
        reverse(
            "delete_purchase", args=[Purchase.objects.get(bill_number="MP/0413").pk]
        )
    )

    assert stock_on_hand(client, elbow) == Decimal(10)
    assert movements(client, elbow) == [(datetime.date(2026, 9, 18), Decimal(10))]

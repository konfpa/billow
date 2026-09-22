import datetime

import pytest
from django.db import IntegrityError
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.purchases.conftest import line, submitted

RECORD = reverse("record_purchase")


def on_file(supplier, bill_date, bill_number="MP/2026-27/0412"):
    purchase = Purchase(
        supplier=supplier,
        bill_number=bill_number,
        bill_date=bill_date,
        received_date=bill_date,
        billed_total=1180,
    )
    purchase.copy_supplier()
    purchase.save()
    return purchase


def record(client, supplier, elbow, bill_date):
    return client.post(
        RECORD, submitted(supplier, line(elbow), bill_date=bill_date.isoformat())
    )


@pytest.mark.django_db
def test_a_bill_entered_twice_is_refused_naming_the_one_on_file(
    client, signed_in, supplier, elbow
):
    on_file(supplier, datetime.date(2026, 4, 1))

    response = record(client, supplier, elbow, datetime.date(2027, 3, 31))

    assert response.status_code == 200
    assert Purchase.objects.count() == 1
    assert (
        "Bill MP/2026-27/0412 from Mehta Pipes dated 1 Apr 2026 is already on file."
        in response.content.decode()
    )


@pytest.mark.django_db
def test_the_same_bill_number_in_another_financial_year_is_accepted(
    client, signed_in, supplier, elbow
):
    on_file(supplier, datetime.date(2026, 3, 31))

    response = record(client, supplier, elbow, datetime.date(2026, 4, 1))

    assert response.status_code == 302
    assert Purchase.objects.count() == 2


@pytest.mark.django_db
def test_the_same_bill_number_from_another_supplier_is_accepted(
    client, signed_in, supplier, karnataka_supplier, elbow
):
    on_file(karnataka_supplier, datetime.date(2026, 9, 18))

    response = record(client, supplier, elbow, datetime.date(2026, 9, 18))

    assert response.status_code == 302
    assert Purchase.objects.count() == 2


@pytest.mark.django_db
def test_the_database_refuses_a_bill_entered_twice(supplier):
    on_file(supplier, datetime.date(2027, 1, 15))

    with pytest.raises(IntegrityError):
        on_file(supplier, datetime.date(2026, 6, 1))

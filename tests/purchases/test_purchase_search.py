import datetime

import pytest
from django.urls import reverse

from tests.purchases.conftest import bill

DIRECTORY = reverse("purchase_directory")


@pytest.fixture
def bills(supplier, karnataka_supplier, elbow):
    """Three bills from two Suppliers across August and September."""
    return [
        bill(supplier, elbow, "MP/0412", datetime.date(2026, 8, 20)),
        bill(supplier, elbow, "MP/0519", datetime.date(2026, 9, 12)),
        bill(karnataka_supplier, elbow, "KF-77", datetime.date(2026, 9, 3)),
    ]


def found(client, **params):
    response = client.get(DIRECTORY, params)
    return [purchase.bill_number for purchase, _ in response.context["purchases"]]


@pytest.mark.django_db
def test_part_of_a_bill_number_finds_the_purchase(client, signed_in, bills):
    assert found(client, q="0519") == ["MP/0519"]


@pytest.mark.django_db
def test_a_supplier_name_finds_their_purchases(client, signed_in, bills):
    assert found(client, q="kaveri") == ["KF-77"]
    assert found(client, q="mehta") == ["MP/0519", "MP/0412"]


@pytest.mark.django_db
def test_a_purchase_is_found_only_if_every_word_matches(client, signed_in, bills):
    assert found(client, q="mehta 0412") == ["MP/0412"]
    assert found(client, q="mehta 77") == []


@pytest.mark.django_db
def test_nothing_matching_says_so(client, signed_in, bills):
    page = client.get(DIRECTORY, {"q": "zzz"}).content.decode()

    assert "No Purchase matches “zzz”" in page


@pytest.mark.django_db
def test_the_directory_filters_by_supplier(
    client, signed_in, bills, karnataka_supplier
):
    assert found(client, supplier=karnataka_supplier.pk) == ["KF-77"]


@pytest.mark.django_db
def test_an_archived_supplier_can_still_be_filtered_by(
    client, signed_in, bills, karnataka_supplier
):
    karnataka_supplier.archive()

    page = client.get(DIRECTORY).content.decode()

    assert f'<option value="{karnataka_supplier.pk}">Kaveri Fittings</option>' in page
    assert found(client, supplier=karnataka_supplier.pk) == ["KF-77"]


@pytest.mark.django_db
def test_a_supplier_not_on_file_filters_nothing(client, signed_in, bills):
    assert len(found(client, supplier="404")) == 3
    assert len(found(client, supplier="mehta")) == 3


@pytest.mark.django_db
def test_the_directory_filters_by_a_range_of_bill_dates(client, signed_in, bills):
    september = {"billed_from": "2026-09-01", "billed_to": "2026-09-30"}

    assert found(client, **september) == ["MP/0519", "KF-77"]


@pytest.mark.django_db
def test_the_range_takes_in_both_ends(client, signed_in, bills):
    assert found(client, billed_from="2026-09-03", billed_to="2026-09-12") == [
        "MP/0519",
        "KF-77",
    ]


@pytest.mark.django_db
def test_either_end_of_the_range_may_be_left_open(client, signed_in, bills):
    assert found(client, billed_from="2026-09-04") == ["MP/0519"]
    assert found(client, billed_to="2026-09-03") == ["KF-77", "MP/0412"]


@pytest.mark.django_db
def test_the_range_is_of_bill_dates_not_received_dates(
    client, signed_in, supplier, elbow
):
    purchase = bill(supplier, elbow, "MP/0431", datetime.date(2026, 9, 2))
    purchase.bill_date = datetime.date(2026, 8, 30)
    purchase.save()

    assert found(client, billed_from="2026-09-01") == []
    assert found(client, billed_to="2026-08-31") == ["MP/0431"]


@pytest.mark.django_db
def test_a_date_that_is_not_one_filters_nothing(client, signed_in, bills):
    assert len(found(client, billed_from="2026-02-30", billed_to="soon")) == 3


@pytest.mark.django_db
def test_nothing_in_the_filters_says_so(client, signed_in, bills, supplier):
    page = client.get(
        DIRECTORY, {"supplier": supplier.pk, "billed_from": "2026-10-01"}
    ).content.decode()

    assert "No Purchases from Mehta Pipes" in page


@pytest.mark.django_db
def test_search_and_filters_combine(client, signed_in, bills, supplier):
    params = {"supplier": supplier.pk, "billed_from": "2026-09-01"}

    assert found(client, q="mp", **params) == ["MP/0519"]
    assert found(client, q="kf", **params) == []


@pytest.mark.django_db
def test_the_filters_are_kept_in_the_form(client, signed_in, bills, supplier):
    page = client.get(
        DIRECTORY,
        {
            "q": "mp",
            "supplier": supplier.pk,
            "billed_from": "2026-09-01",
            "billed_to": "2026-09-30",
        },
    ).content.decode()

    assert 'value="mp"' in page
    assert f'<option value="{supplier.pk}" selected>Mehta Pipes</option>' in page
    assert 'value="2026-09-01"' in page
    assert 'value="2026-09-30"' in page


@pytest.mark.django_db
def test_the_count_says_how_many_of_all_are_shown(client, signed_in, bills, supplier):
    page = client.get(DIRECTORY, {"supplier": supplier.pk}).content.decode()

    assert "2 of 3 recorded" in page

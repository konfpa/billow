import pytest
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.purchases.conftest import line, submitted

RECORD = reverse("record_purchase")


def recorded(client, supplier, *rows, **changes):
    client.post(RECORD, submitted(supplier, *rows, **changes))
    return Purchase.objects.latest("pk")


def detail(client, purchase):
    return client.get(reverse("purchase_detail", args=[purchase.pk])).content.decode()


@pytest.mark.django_db
def test_the_page_shows_the_bill(client, signed_in, supplier, elbow):
    purchase = recorded(client, supplier, line(elbow), received_date="2026-09-21")

    page = detail(client, purchase)

    for shown in (
        "Mehta Pipes",
        "MP/2026-27/0412",
        "18 September 2026",
        "21 September 2026",
        "CPVC elbow ¾ inch",
        "10 NOS",
    ):
        assert shown in page


@pytest.mark.django_db
def test_within_the_state_tax_is_cgst_and_sgst(client, signed_in, supplier, elbow):
    purchase = recorded(
        client, supplier, line(elbow, quantity="3", rate="100"), billed_total="354"
    )

    page = detail(client, purchase)

    assert ">CGST</th>" in page
    assert ">SGST</th>" in page
    assert ">IGST</th>" not in page
    assert "₹27.00" in page
    assert "₹354.00" in page


@pytest.mark.django_db
def test_from_another_state_tax_is_igst(client, signed_in, karnataka_supplier, elbow):
    purchase = recorded(
        client,
        karnataka_supplier,
        line(elbow, quantity="3", rate="100"),
        billed_total="354",
    )

    page = detail(client, purchase)

    assert ">IGST</th>" in page
    assert ">CGST</th>" not in page
    assert "₹54.00" in page
    assert "₹354.00" in page


@pytest.mark.django_db
def test_an_unregistered_supplier_charges_no_tax(
    client, signed_in, unregistered_supplier, elbow
):
    purchase = recorded(
        client,
        unregistered_supplier,
        line(elbow, quantity="3", rate="100"),
        billed_total="300",
    )

    page = detail(client, purchase)

    assert "No tax, from an unregistered Supplier" in page
    assert ">CGST</th>" not in page
    assert ">IGST</th>" not in page
    assert "Grand total" in page
    assert "₹300.00" in page


@pytest.mark.django_db
def test_tax_is_shown_by_gst_rate(client, signed_in, supplier, elbow, pipe):
    purchase = recorded(
        client,
        supplier,
        line(elbow, quantity="2", rate="100"),
        line(pipe, quantity="1", rate="200"),
        billed_total="446",
    )

    page = detail(client, purchase)

    assert "Tax by GST rate" in page
    assert ">5%</td>" in page
    assert ">18%</td>" in page
    assert "₹446.00" in page


@pytest.mark.django_db
def test_correcting_the_supplier_later_leaves_the_tax_as_it_was(
    client, signed_in, supplier, elbow
):
    purchase = recorded(
        client, supplier, line(elbow, quantity="3", rate="100"), billed_total="354"
    )

    supplier.gstin = ""
    supplier.save()

    page = detail(client, purchase)
    assert ">CGST</th>" in page
    assert "₹354.00" in page
    assert "27AAACM1234K1ZN" in page


@pytest.mark.django_db
def test_a_purchase_from_a_since_archived_supplier_still_shows(
    client, signed_in, supplier, elbow
):
    purchase = recorded(client, supplier, line(elbow))
    supplier.archive()
    elbow.archive()

    page = detail(client, purchase)

    assert "Mehta Pipes" in page
    assert "CPVC elbow ¾ inch" in page


@pytest.mark.django_db
def test_recording_says_the_bill_is_saved(client, signed_in, supplier, elbow):
    response = client.post(RECORD, submitted(supplier, line(elbow)), follow=True)

    assert "Bill MP/2026-27/0412 from Mehta Pipes is saved." in (
        response.content.decode()
    )

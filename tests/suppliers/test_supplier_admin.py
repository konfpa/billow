import pytest
from django.urls import reverse

from apps.suppliers.models import Supplier

CHANGELIST = reverse("admin:suppliers_supplier_changelist")


def change_url(supplier):
    return reverse("admin:suppliers_supplier_change", args=[supplier.pk])


def history_url(supplier):
    return reverse("admin:suppliers_supplier_history", args=[supplier.pk])


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.mark.django_db
def test_the_admin_shows_every_detail_of_a_supplier(superuser_client, supplier):
    page = superuser_client.get(change_url(supplier)).content.decode()

    for detail in (
        "Mehta Pipes",
        "Mehta Pipes Private Limited",
        "Plot 14, MIDC<br>Bhosari",
        "Pune",
        "411026",
        "Maharashtra",
        "27AAACM1234K1ZN",
        "sales@mehtapipes.example.com",
        "+91 20 5555 0142",
    ):
        assert f'<div class="readonly">{detail}</div>' in page


@pytest.mark.django_db
def test_the_listing_identifies_a_supplier_by_state_and_gstin(
    superuser_client, supplier
):
    page = superuser_client.get(CHANGELIST).content.decode()

    assert "Mehta Pipes" in page
    assert '<td class="field-state">Maharashtra</td>' in page
    assert "27AAACM1234K1ZN" in page


@pytest.mark.django_db
def test_the_admin_shows_archived_suppliers(superuser_client, supplier):
    supplier.archive()

    listing = superuser_client.get(CHANGELIST)
    detail = superuser_client.get(change_url(supplier))

    assert "Mehta Pipes" in listing.content.decode()
    assert detail.status_code == 200


@pytest.mark.django_db
def test_the_admin_offers_no_way_to_change_a_supplier(superuser_client, supplier):
    page = superuser_client.get(change_url(supplier)).content.decode()

    assert 'name="_save"' not in page
    assert '<input type="text" name="name"' not in page


@pytest.mark.django_db
def test_a_change_posted_to_the_admin_is_not_made(superuser_client, supplier):
    superuser_client.post(
        change_url(supplier), {"name": "Someone Else Traders", "_save": ""}
    )

    supplier.refresh_from_db()
    assert supplier.name == "Mehta Pipes"


@pytest.mark.django_db
def test_the_admin_cannot_add_a_supplier(superuser_client):
    response = superuser_client.get(reverse("admin:suppliers_supplier_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_the_admin_cannot_delete_a_supplier(superuser_client, supplier):
    response = superuser_client.post(
        reverse("admin:suppliers_supplier_delete", args=[supplier.pk]),
        {"post": "yes"},
    )

    assert response.status_code == 403
    assert Supplier.including_archived.filter(pk=supplier.pk).exists()


@pytest.mark.django_db
def test_the_admin_shows_who_changed_a_supplier(superuser_client, superuser, supplier):
    supplier._history_user = superuser  # noqa: SLF001 — simple_history's documented hook
    supplier.city = "Thane"
    supplier.save()

    page = superuser_client.get(history_url(supplier)).content.decode()

    assert "Priya Nair" in page

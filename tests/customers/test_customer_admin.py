import pytest
from django.urls import reverse

from apps.customers.models import Customer

CHANGELIST = reverse("admin:customers_customer_changelist")


def change_url(customer):
    return reverse("admin:customers_customer_change", args=[customer.pk])


def history_url(customer):
    return reverse("admin:customers_customer_history", args=[customer.pk])


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.mark.django_db
def test_the_admin_shows_every_detail_of_a_customer(superuser_client, customer):
    page = superuser_client.get(change_url(customer)).content.decode()

    for detail in (
        "Sharma Traders",
        "Sharma Traders LLP",
        "22 Linking Road",
        "Bandra West",
        "Mumbai",
        "400050",
        "Maharashtra",
        "27AAPFU0939F1ZV",
        "accounts@sharma.example.com",
        "+91 22 5555 0199",
    ):
        assert f'<div class="readonly">{detail}</div>' in page


@pytest.mark.django_db
def test_the_listing_identifies_a_customer_by_state_and_gstin(
    superuser_client, customer
):
    page = superuser_client.get(CHANGELIST).content.decode()

    assert "Sharma Traders" in page
    assert '<td class="field-state">Maharashtra</td>' in page
    assert "27AAPFU0939F1ZV" in page


@pytest.mark.django_db
def test_the_admin_shows_archived_customers(superuser_client, customer):
    customer.archive()

    listing = superuser_client.get(CHANGELIST)
    detail = superuser_client.get(change_url(customer))

    assert "Sharma Traders" in listing.content.decode()
    assert detail.status_code == 200


@pytest.mark.django_db
def test_the_admin_offers_no_way_to_change_a_customer(superuser_client, customer):
    page = superuser_client.get(change_url(customer)).content.decode()

    assert 'name="_save"' not in page
    assert '<input type="text" name="name"' not in page


@pytest.mark.django_db
def test_a_change_posted_to_the_admin_is_not_made(superuser_client, customer):
    superuser_client.post(
        change_url(customer), {"name": "Someone Else Traders", "_save": ""}
    )

    customer.refresh_from_db()
    assert customer.name == "Sharma Traders"


@pytest.mark.django_db
def test_the_admin_cannot_add_a_customer(superuser_client):
    response = superuser_client.get(reverse("admin:customers_customer_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_the_admin_cannot_delete_a_customer(superuser_client, customer):
    response = superuser_client.post(
        reverse("admin:customers_customer_delete", args=[customer.pk]),
        {"post": "yes"},
    )

    assert response.status_code == 403
    assert Customer.including_archived.filter(pk=customer.pk).exists()


@pytest.mark.django_db
def test_the_admin_shows_who_changed_a_customer(superuser_client, superuser, customer):
    customer._history_user = superuser  # noqa: SLF001 — simple_history's documented hook
    customer.city = "Thane"
    customer.save()

    page = superuser_client.get(history_url(customer)).content.decode()

    assert "Priya Nair" in page

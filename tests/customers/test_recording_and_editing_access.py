import pytest
from django.urls import reverse

from apps.customers.models import Customer
from tests.conftest import role
from tests.customers.conftest import submitted

RECORD = reverse("record_customer")
DIRECTORY = reverse("customer_directory")
HOME = reverse("home")


def edit_page(customer):
    return reverse("edit_customer", args=[customer.pk])


def detail_page(customer):
    return reverse("customer_detail", args=[customer.pk])


@pytest.fixture
def looker(powerless):
    """A User who may read Customers and do nothing else to them."""
    powerless.groups.add(role("Looker", "customers.view_customer"))
    return powerless


@pytest.mark.django_db
def test_without_add_customer_recording_is_refused(client, business, looker):
    client.force_login(looker)

    for response in (client.get(RECORD), client.post(RECORD, submitted())):
        assert response.status_code == 403
        assert "Can add customer" in response.content.decode()

    assert not Customer.including_archived.exists()


@pytest.mark.django_db
def test_add_customer_through_a_role_records_a_customer(client, business, powerless):
    powerless.groups.add(role("Recorder", "customers.add_customer"))
    client.force_login(powerless)

    assert client.get(RECORD).status_code == 200
    response = client.post(RECORD, submitted())

    assert response.status_code == 302
    assert Customer.objects.get().name == "Sharma Traders"


@pytest.mark.django_db
def test_without_change_customer_editing_is_refused(client, business, looker, customer):
    client.force_login(looker)

    for response in (
        client.get(edit_page(customer)),
        client.post(edit_page(customer), submitted(city="Pune")),
    ):
        assert response.status_code == 403
        assert "Can change customer" in response.content.decode()

    customer.refresh_from_db()
    assert customer.city == "Mumbai"


@pytest.mark.django_db
def test_change_customer_through_a_role_edits_a_customer(
    client, business, powerless, customer
):
    powerless.groups.add(role("Corrector", "customers.change_customer"))
    client.force_login(powerless)

    assert client.get(edit_page(customer)).status_code == 200
    response = client.post(edit_page(customer), submitted(city="Pune"))

    assert response.status_code == 302
    customer.refresh_from_db()
    assert customer.city == "Pune"


@pytest.mark.django_db
def test_record_controls_are_hidden_without_add_customer(client, business, looker):
    client.force_login(looker)

    for url in (HOME, DIRECTORY):
        page = client.get(url).content.decode()

        assert 'data-tip="New Customer"' not in page, url
        assert f'href="{RECORD}"' not in page, url


@pytest.mark.django_db
def test_record_controls_are_shown_with_add_customer(client, business, looker):
    looker.groups.add(role("Recorder", "customers.add_customer"))
    client.force_login(looker)

    for url in (HOME, DIRECTORY):
        page = client.get(url).content.decode()

        assert 'data-tip="New Customer"' in page, url

    directory = client.get(DIRECTORY).content.decode()
    assert '<i data-lucide="plus" class="size-4"></i>New Customer' in directory


@pytest.mark.django_db
def test_edit_control_is_hidden_without_change_customer(
    client, business, looker, customer
):
    client.force_login(looker)

    page = client.get(detail_page(customer)).content.decode()

    assert f'href="{edit_page(customer)}"' not in page


@pytest.mark.django_db
def test_edit_control_is_shown_with_change_customer(client, business, looker, customer):
    looker.groups.add(role("Corrector", "customers.change_customer"))
    client.force_login(looker)

    page = client.get(detail_page(customer)).content.decode()

    assert f'href="{edit_page(customer)}"' in page

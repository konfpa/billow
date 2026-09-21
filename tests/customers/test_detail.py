import pytest
from django.urls import reverse

from apps.customers.models import Customer
from tests.customers.conftest import submitted

DIRECTORY = reverse("customer_directory")


def detail_url(customer):
    return reverse("customer_detail", args=[customer.pk])


@pytest.fixture
def unregistered(db):
    return Customer.objects.create(
        **submitted(
            name="Anita Desai",
            legal_name="",
            gstin="",
            address="Unit 4\nMG Road",
            city="Bengaluru",
            postal_code="560001",
            state="29",
            email="",
            phone="",
        ),
    )


@pytest.mark.django_db
def test_a_customer_on_file_is_shown(client, signed_in, customer):
    response = client.get(detail_url(customer))

    assert response.status_code == 200
    page = response.content.decode()
    assert "Sharma Traders LLP" in page
    assert "27AAPFU0939F1ZV" in page
    assert "accounts@sharma.example.com" in page
    assert "+91 22 5555 0199" in page


@pytest.mark.django_db
def test_an_archived_customer_is_shown(client, signed_in, archived):
    response = client.get(detail_url(archived))

    assert response.status_code == 200
    assert "Archived on" in response.content.decode()


@pytest.mark.django_db
def test_a_customer_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.get(reverse("customer_detail", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_viewing_requires_signing_in(client, customer):
    url = detail_url(customer)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


@pytest.mark.django_db
def test_the_address_on_record_is_shown_line_by_line(client, signed_in, unregistered):
    page = client.get(detail_url(unregistered)).content.decode()

    address = page[page.index("Unit 4<br>MG Road") :]
    assert address.index("Bengaluru") < address.index("560001")
    assert address.index("560001") < address.index("Karnataka")


@pytest.mark.django_db
def test_a_customer_without_a_gstin_is_unregistered(client, signed_in, unregistered):
    page = client.get(detail_url(unregistered)).content.decode()

    assert ">Unregistered</dd>" in page


@pytest.mark.django_db
def test_a_blank_legal_name_is_not_shown_separately(client, signed_in, unregistered):
    page = client.get(detail_url(unregistered)).content.decode()

    assert "Legal name" not in page


@pytest.mark.django_db
def test_a_differing_legal_name_is_shown(client, signed_in, customer):
    page = client.get(detail_url(customer)).content.decode()

    assert "Legal name" in page


@pytest.mark.django_db
def test_the_back_link_returns_to_the_directory(client, signed_in, customer):
    page = client.get(detail_url(customer)).content.decode()

    assert f'href="{DIRECTORY}"' in page


@pytest.mark.django_db
def test_the_back_link_returns_an_archived_customer_to_the_filter(
    client,
    signed_in,
    archived,
):
    page = client.get(detail_url(archived)).content.decode()

    assert f'href="{DIRECTORY}?show=archived"' in page


@pytest.mark.django_db
def test_the_customer_is_edited_from_here(client, signed_in, customer):
    page = client.get(detail_url(customer)).content.decode()

    assert f'href="{reverse("edit_customer", args=[customer.pk])}"' in page

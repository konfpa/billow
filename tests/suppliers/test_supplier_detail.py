import pytest
from django.urls import reverse

from apps.suppliers.models import Supplier
from tests.suppliers.conftest import submitted

DIRECTORY = reverse("supplier_directory")


def detail_url(supplier):
    return reverse("supplier_detail", args=[supplier.pk])


@pytest.fixture
def unregistered(db):
    return Supplier.objects.create(
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
def test_a_supplier_on_file_is_shown(client, signed_in, supplier):
    response = client.get(detail_url(supplier))

    assert response.status_code == 200
    page = response.content.decode()
    assert "Mehta Pipes Private Limited" in page
    assert "27AAACM1234K1ZN" in page
    assert "sales@mehtapipes.example.com" in page
    assert "+91 20 5555 0142" in page


@pytest.mark.django_db
def test_an_archived_supplier_is_shown(client, signed_in, archived):
    response = client.get(detail_url(archived))

    assert response.status_code == 200
    assert "Archived on" in response.content.decode()


@pytest.mark.django_db
def test_a_supplier_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.get(reverse("supplier_detail", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_viewing_requires_signing_in(client, supplier):
    url = detail_url(supplier)

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
def test_a_supplier_without_a_gstin_is_unregistered(client, signed_in, unregistered):
    page = client.get(detail_url(unregistered)).content.decode()

    assert ">Unregistered</dd>" in page


@pytest.mark.django_db
def test_a_blank_legal_name_is_not_shown_separately(client, signed_in, unregistered):
    page = client.get(detail_url(unregistered)).content.decode()

    assert "Legal name" not in page


@pytest.mark.django_db
def test_a_differing_legal_name_is_shown(client, signed_in, supplier):
    page = client.get(detail_url(supplier)).content.decode()

    assert "Legal name" in page


@pytest.mark.django_db
def test_the_back_link_returns_to_the_directory(client, signed_in, supplier):
    page = client.get(detail_url(supplier)).content.decode()

    assert f'href="{DIRECTORY}"' in page


@pytest.mark.django_db
def test_the_back_link_returns_an_archived_supplier_to_the_filter(
    client,
    signed_in,
    archived,
):
    page = client.get(detail_url(archived)).content.decode()

    assert f'href="{DIRECTORY}?show=archived"' in page


@pytest.mark.django_db
def test_the_supplier_is_edited_from_here(client, signed_in, supplier):
    page = client.get(detail_url(supplier)).content.decode()

    assert f'href="{reverse("edit_supplier", args=[supplier.pk])}"' in page

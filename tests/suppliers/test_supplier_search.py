import pytest
from django.urls import reverse

from apps.suppliers.models import Supplier
from tests.suppliers.conftest import submitted

DIRECTORY = reverse("supplier_directory")


@pytest.fixture
def another(db):
    return Supplier.objects.create(
        **submitted(name="Anita Desai", legal_name="", gstin=""),
    )


def found(client, query, **params):
    response = client.get(DIRECTORY, {"q": query, **params})
    return [supplier.name for supplier in response.context["suppliers"]]


@pytest.mark.django_db
def test_part_of_a_display_name_finds_the_supplier(
    client,
    signed_in,
    supplier,
    another,
):
    assert found(client, "Mehta") == ["Mehta Pipes"]


@pytest.mark.django_db
def test_a_legal_name_finds_the_supplier(client, signed_in, supplier, another):
    assert found(client, "Private Limited") == ["Mehta Pipes"]


@pytest.mark.django_db
@pytest.mark.parametrize("typed", ["27AAACM1234K1ZN", "27aaacm1234k1zn"])
def test_a_gstin_finds_the_supplier_whatever_its_case(
    client,
    signed_in,
    supplier,
    another,
    typed,
):
    assert found(client, typed) == ["Mehta Pipes"]


@pytest.mark.django_db
def test_search_ignores_case_and_matches_part_of_a_name(
    client,
    signed_in,
    supplier,
    another,
):
    assert found(client, "hta pi") == ["Mehta Pipes"]


@pytest.mark.django_db
def test_a_search_matching_nothing_says_so(client, signed_in, supplier):
    page = client.get(DIRECTORY, {"q": "Kapoor"}).content.decode()

    assert "No Supplier matches “Kapoor”" in page
    assert "Nobody on file yet" not in page


@pytest.mark.django_db
def test_a_search_matching_nothing_points_to_the_archived(client, signed_in):
    page = client.get(DIRECTORY, {"q": "Kapoor"}).content.decode()

    assert f'href="{DIRECTORY}?show=archived&amp;q=Kapoor"' in page


@pytest.mark.django_db
def test_searching_the_directory_leaves_the_archived_out(client, signed_in, supplier):
    supplier.archive()

    assert found(client, "Mehta") == []


@pytest.mark.django_db
def test_searching_the_archived_finds_them(client, signed_in, supplier, another):
    supplier.archive()
    another.archive()

    assert found(client, "Mehta", show="archived") == ["Mehta Pipes"]


@pytest.mark.django_db
def test_searching_the_archived_leaves_those_on_file_out(client, signed_in, supplier):
    assert found(client, "Mehta", show="archived") == []


@pytest.mark.django_db
def test_the_search_box_on_the_archived_view_searches_the_archived(
    client,
    signed_in,
):
    page = client.get(DIRECTORY, {"show": "archived"}).content.decode()

    assert '<input type="hidden" name="show" value="archived">' in page


@pytest.mark.django_db
def test_the_search_box_keeps_what_was_searched(client, signed_in, supplier):
    page = client.get(DIRECTORY, {"q": "Mehta"}).content.decode()

    assert 'name="q" value="Mehta"' in page

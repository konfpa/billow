import pytest
from django.urls import reverse

from apps.customers.models import Customer
from tests.customers.conftest import submitted

DIRECTORY = reverse("customer_directory")


@pytest.fixture
def another(db):
    return Customer.objects.create(
        **submitted(name="Anita Desai", legal_name="", gstin=""),
    )


def found(client, query, **params):
    response = client.get(DIRECTORY, {"q": query, **params})
    return [customer.name for customer in response.context["customers"]]


@pytest.mark.django_db
def test_part_of_a_display_name_finds_the_customer(
    client,
    signed_in,
    customer,
    another,
):
    assert found(client, "Sharma") == ["Sharma Traders"]


@pytest.mark.django_db
def test_a_legal_name_finds_the_customer(client, signed_in, customer, another):
    assert found(client, "Traders LLP") == ["Sharma Traders"]


@pytest.mark.django_db
@pytest.mark.parametrize("typed", ["27AAPFU0939F1ZV", "27aapfu0939f1zv"])
def test_a_gstin_finds_the_customer_whatever_its_case(
    client,
    signed_in,
    customer,
    another,
    typed,
):
    assert found(client, typed) == ["Sharma Traders"]


@pytest.mark.django_db
def test_search_ignores_case_and_matches_part_of_a_name(
    client,
    signed_in,
    customer,
    another,
):
    assert found(client, "arma tra") == ["Sharma Traders"]


@pytest.mark.django_db
def test_a_search_matching_nothing_says_so(client, signed_in, customer):
    page = client.get(DIRECTORY, {"q": "Kapoor"}).content.decode()

    assert "No Customer matches “Kapoor”" in page
    assert "Nobody on file yet" not in page


@pytest.mark.django_db
def test_a_search_matching_nothing_points_to_the_archived(client, signed_in):
    page = client.get(DIRECTORY, {"q": "Kapoor"}).content.decode()

    assert f'href="{DIRECTORY}?show=archived&amp;q=Kapoor"' in page


@pytest.mark.django_db
def test_searching_the_directory_leaves_the_archived_out(client, signed_in, customer):
    customer.archive()

    assert found(client, "Sharma") == []


@pytest.mark.django_db
def test_searching_the_archived_finds_them(client, signed_in, customer, another):
    customer.archive()
    another.archive()

    assert found(client, "Sharma", show="archived") == ["Sharma Traders"]


@pytest.mark.django_db
def test_searching_the_archived_leaves_those_on_file_out(client, signed_in, customer):
    assert found(client, "Sharma", show="archived") == []


@pytest.mark.django_db
def test_the_search_box_on_the_archived_view_searches_the_archived(
    client,
    signed_in,
):
    page = client.get(DIRECTORY, {"show": "archived"}).content.decode()

    assert '<input type="hidden" name="show" value="archived">' in page


@pytest.mark.django_db
def test_the_search_box_keeps_what_was_searched(client, signed_in, customer):
    page = client.get(DIRECTORY, {"q": "Sharma"}).content.decode()

    assert 'name="q" value="Sharma"' in page

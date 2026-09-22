import pytest
from django.urls import reverse

from tests.conftest import role

HOME = reverse("home")
NO_WORK = "Nothing on Home is open to you yet"


@pytest.mark.django_db
def test_a_user_with_no_role_is_told_to_ask_a_superuser(client, business, powerless):
    client.force_login(powerless)

    response = client.get(HOME)
    page = response.content.decode()

    assert response.status_code == 200
    assert NO_WORK in page
    assert "A Superuser grants Roles, so please ask one." in page
    assert "Group" not in page
    assert 'data-kui="empty-state/permission"' in page


@pytest.mark.django_db
def test_viewing_customers_offers_the_directory(client, business, powerless):
    powerless.groups.add(role("Looker", "customers.view_customer"))
    client.force_login(powerless)

    page = client.get(HOME).content.decode()

    assert "Open the directory" in page
    assert reverse("customer_directory") in page
    assert NO_WORK not in page


@pytest.mark.django_db
def test_without_viewing_customers_the_directory_is_not_offered(
    client, business, powerless
):
    powerless.groups.add(role("Business reader", "business.view_business"))
    client.force_login(powerless)

    page = client.get(HOME).content.decode()

    assert "Open the directory" not in page


@pytest.mark.django_db
def test_viewing_suppliers_offers_their_directory(client, business, powerless):
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)

    page = client.get(HOME).content.decode()

    assert 'id="home-suppliers-h"' in page
    assert reverse("supplier_directory") in page
    assert 'id="home-customers-h"' not in page
    assert NO_WORK not in page


@pytest.mark.django_db
def test_without_viewing_suppliers_their_directory_is_not_offered(
    client, business, powerless
):
    powerless.groups.add(role("Looker", "customers.view_customer"))
    client.force_login(powerless)

    page = client.get(HOME).content.decode()

    assert 'id="home-suppliers-h"' not in page
    assert reverse("supplier_directory") not in page

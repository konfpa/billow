import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from tests.conftest import PASSWORD, role

DIRECTORY = reverse("customer_directory")


def pages(customer):
    """Every page that reads the Customer directory or one Customer on file."""
    return [
        DIRECTORY,
        f"{DIRECTORY}?show=archived",
        f"{DIRECTORY}?q=Sharma",
        f"{DIRECTORY}?show=archived&q=Sharma",
        reverse("customer_detail", args=[customer.pk]),
    ]


@pytest.mark.django_db
def test_without_view_customer_every_customer_page_is_refused(
    client, business, powerless, customer
):
    client.force_login(powerless)

    for url in pages(customer):
        response = client.get(url)

        assert response.status_code == 403, url
        page = response.content.decode()
        assert "Can view customer" in page
        assert "Superuser" in page


@pytest.mark.django_db
def test_the_refusal_says_role_rather_than_group(client, business, powerless, customer):
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert "Role" in page
    assert "Group" not in page


@pytest.mark.django_db
def test_the_refusal_sits_inside_the_app(client, business, powerless, customer):
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert 'data-kui="app-shell/default"' in page
    assert 'aria-label="Main"' in page


@pytest.mark.django_db
def test_view_customer_through_a_role_opens_every_customer_page(
    client, business, powerless, customer
):
    powerless.groups.add(role("Looker", "customers.view_customer"))
    client.force_login(powerless)

    for url in pages(customer):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_view_customer_granted_directly_opens_every_customer_page(
    client, business, powerless, customer
):
    powerless.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="customers", codename="view_customer"
        )
    )
    client.force_login(powerless)

    for url in pages(customer):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_a_superuser_with_no_role_opens_every_customer_page(
    client, business, superuser, customer
):
    client.force_login(superuser)

    for url in pages(customer):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_an_anonymous_visitor_is_sent_to_sign_in(client, business, customer):
    for url in pages(customer):
        response = client.get(url)

        assert response.status_code == 302, url
        assert response.url.startswith(f"{reverse('login')}?next=")


@pytest.mark.django_db
def test_the_customers_link_is_hidden_without_view_customer(
    client, business, powerless
):
    client.force_login(powerless)

    page = client.get(reverse("home")).content.decode()

    assert 'data-tip="Customers"' not in page


@pytest.mark.django_db
def test_the_customers_link_is_shown_with_view_customer(client, business, powerless):
    powerless.groups.add(role("Looker", "customers.view_customer"))
    client.force_login(powerless)

    page = client.get(reverse("home")).content.decode()

    assert 'data-tip="Customers"' in page


@pytest.mark.django_db
def test_a_deactivated_user_holding_a_role_cannot_sign_in(client, business, operator):
    operator.is_active = False
    operator.save()

    client.post(
        reverse("login"),
        {"username": operator.email, "password": PASSWORD},
    )

    assert "_auth_user_id" not in client.session

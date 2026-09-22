import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from tests.conftest import role

DIRECTORY = reverse("supplier_directory")


def pages(supplier):
    """Every page that reads the Supplier directory or one Supplier on file."""
    return [
        DIRECTORY,
        f"{DIRECTORY}?show=archived",
        f"{DIRECTORY}?q=Mehta",
        f"{DIRECTORY}?show=archived&q=Mehta",
        reverse("supplier_detail", args=[supplier.pk]),
    ]


@pytest.mark.django_db
def test_without_view_supplier_every_supplier_page_is_refused(
    client, business, powerless, supplier
):
    client.force_login(powerless)

    for url in pages(supplier):
        response = client.get(url)

        assert response.status_code == 403, url
        page = response.content.decode()
        assert "Can view supplier" in page
        assert "Superuser" in page


@pytest.mark.django_db
def test_the_refusal_says_role_rather_than_group(client, business, powerless, supplier):
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert "Role" in page
    assert "Group" not in page


@pytest.mark.django_db
def test_the_refusal_sits_inside_the_app(client, business, powerless, supplier):
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert 'data-kui="app-shell/default"' in page
    assert 'aria-label="Main"' in page


@pytest.mark.django_db
def test_view_supplier_through_a_role_opens_every_supplier_page(
    client, business, powerless, supplier
):
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)

    for url in pages(supplier):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_view_supplier_granted_directly_opens_every_supplier_page(
    client, business, powerless, supplier
):
    powerless.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="suppliers", codename="view_supplier"
        )
    )
    client.force_login(powerless)

    for url in pages(supplier):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_a_superuser_with_no_role_opens_every_supplier_page(
    client, business, superuser, supplier
):
    client.force_login(superuser)

    for url in pages(supplier):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_an_anonymous_visitor_is_sent_to_sign_in(client, business, supplier):
    for url in pages(supplier):
        response = client.get(url)

        assert response.status_code == 302, url
        assert response.url.startswith(f"{reverse('login')}?next=")


@pytest.mark.django_db
def test_the_suppliers_link_is_hidden_without_view_supplier(
    client, business, powerless
):
    client.force_login(powerless)

    page = client.get(reverse("home")).content.decode()

    assert 'data-tip="Suppliers"' not in page


@pytest.mark.django_db
def test_the_suppliers_link_is_shown_with_view_supplier(client, business, powerless):
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    client.force_login(powerless)

    page = client.get(reverse("home")).content.decode()

    assert 'data-tip="Suppliers"' in page


@pytest.mark.django_db
def test_the_suppliers_link_follows_the_customers_link(client, business, looker):
    looker.groups.add(role("Customer looker", "customers.view_customer"))
    client.force_login(looker)

    page = client.get(reverse("home")).content.decode()

    assert page.index('data-tip="Customers"') < page.index('data-tip="Suppliers"')


def suppliers_link(page):
    """The opening tag of the sidebar's Suppliers link."""
    start = page.index('data-tip="Suppliers"')
    return page[start : page.index(">", start)]


@pytest.mark.django_db
def test_the_suppliers_link_is_current_on_every_supplier_page(
    client, business, superuser, supplier
):
    client.force_login(superuser)

    for url in (
        DIRECTORY,
        reverse("record_supplier"),
        reverse("supplier_detail", args=[supplier.pk]),
        reverse("edit_supplier", args=[supplier.pk]),
    ):
        page = client.get(url).content.decode()

        assert 'aria-current="page"' in suppliers_link(page), url


@pytest.mark.django_db
def test_the_suppliers_link_is_not_current_elsewhere(client, business, superuser):
    client.force_login(superuser)

    page = client.get(reverse("customer_directory")).content.decode()

    assert 'aria-current="page"' not in suppliers_link(page)

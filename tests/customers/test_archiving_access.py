import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from tests.conftest import role


def archive_url(customer):
    return reverse("archive_customer", args=[customer.pk])


def restore_url(customer):
    return reverse("restore_customer", args=[customer.pk])


def detail_html(client, customer):
    url = reverse("customer_detail", args=[customer.pk])
    return client.get(url).content.decode()


@pytest.fixture
def archivist(looker):
    looker.groups.add(role("Archivist", "customers.archive_customer"))
    return looker


@pytest.mark.django_db
def test_archive_customer_is_named_as_the_admin_shows_it():
    permission = Permission.objects.get(
        content_type__app_label="customers", codename="archive_customer"
    )

    assert permission.name == "Can archive customer"


@pytest.mark.django_db
def test_without_archive_customer_archiving_is_refused(
    client, business, looker, customer
):
    client.force_login(looker)

    response = client.post(archive_url(customer))

    assert response.status_code == 403
    assert "Can archive customer" in response.content.decode()
    customer.refresh_from_db()
    assert not customer.is_archived


@pytest.mark.django_db
def test_without_archive_customer_restoring_is_refused(
    client, business, looker, archived
):
    client.force_login(looker)

    response = client.post(restore_url(archived))

    assert response.status_code == 403
    assert "Can archive customer" in response.content.decode()
    archived.refresh_from_db()
    assert archived.is_archived


@pytest.mark.django_db
def test_change_customer_alone_neither_archives_nor_restores(
    client, business, looker, customer
):
    looker.groups.add(role("Corrector", "customers.change_customer"))
    client.force_login(looker)

    assert client.post(archive_url(customer)).status_code == 403
    customer.refresh_from_db()
    assert not customer.is_archived

    customer.archive()
    assert client.post(restore_url(customer)).status_code == 403
    customer.refresh_from_db()
    assert customer.is_archived


@pytest.mark.django_db
def test_archive_customer_through_a_role_archives_and_restores(
    client, business, archivist, customer
):
    client.force_login(archivist)

    assert client.post(archive_url(customer)).status_code == 302
    customer.refresh_from_db()
    assert customer.is_archived

    assert client.post(restore_url(customer)).status_code == 302
    customer.refresh_from_db()
    assert not customer.is_archived


@pytest.mark.django_db
def test_archive_and_restore_controls_are_hidden_without_archive_customer(
    client, business, looker, customer
):
    client.force_login(looker)

    assert f'action="{archive_url(customer)}"' not in detail_html(client, customer)

    customer.archive()
    assert f'action="{restore_url(customer)}"' not in detail_html(client, customer)


@pytest.mark.django_db
def test_archive_and_restore_controls_are_shown_with_archive_customer(
    client, business, archivist, customer
):
    client.force_login(archivist)

    assert f'action="{archive_url(customer)}"' in detail_html(client, customer)

    customer.archive()
    assert f'action="{restore_url(customer)}"' in detail_html(client, customer)

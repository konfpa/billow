import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from tests.conftest import role


def archive_url(supplier):
    return reverse("archive_supplier", args=[supplier.pk])


def restore_url(supplier):
    return reverse("restore_supplier", args=[supplier.pk])


def detail_html(client, supplier):
    url = reverse("supplier_detail", args=[supplier.pk])
    return client.get(url).content.decode()


@pytest.fixture
def archivist(looker):
    looker.groups.add(role("Archivist", "suppliers.archive_supplier"))
    return looker


@pytest.mark.django_db
def test_archive_supplier_is_named_as_the_admin_shows_it():
    permission = Permission.objects.get(
        content_type__app_label="suppliers", codename="archive_supplier"
    )

    assert permission.name == "Can archive supplier"


@pytest.mark.django_db
def test_without_archive_supplier_archiving_is_refused(
    client, business, looker, supplier
):
    client.force_login(looker)

    response = client.post(archive_url(supplier))

    assert response.status_code == 403
    assert "Can archive supplier" in response.content.decode()
    supplier.refresh_from_db()
    assert not supplier.is_archived


@pytest.mark.django_db
def test_without_archive_supplier_restoring_is_refused(
    client, business, looker, archived
):
    client.force_login(looker)

    response = client.post(restore_url(archived))

    assert response.status_code == 403
    assert "Can archive supplier" in response.content.decode()
    archived.refresh_from_db()
    assert archived.is_archived


@pytest.mark.django_db
def test_change_supplier_alone_neither_archives_nor_restores(
    client, business, looker, supplier
):
    looker.groups.add(role("Corrector", "suppliers.change_supplier"))
    client.force_login(looker)

    assert client.post(archive_url(supplier)).status_code == 403
    supplier.refresh_from_db()
    assert not supplier.is_archived

    supplier.archive()
    assert client.post(restore_url(supplier)).status_code == 403
    supplier.refresh_from_db()
    assert supplier.is_archived


@pytest.mark.django_db
def test_archive_supplier_through_a_role_archives_and_restores(
    client, business, archivist, supplier
):
    client.force_login(archivist)

    assert client.post(archive_url(supplier)).status_code == 302
    supplier.refresh_from_db()
    assert supplier.is_archived

    assert client.post(restore_url(supplier)).status_code == 302
    supplier.refresh_from_db()
    assert not supplier.is_archived


@pytest.mark.django_db
def test_archive_and_restore_controls_are_hidden_without_archive_supplier(
    client, business, looker, supplier
):
    client.force_login(looker)

    assert f'action="{archive_url(supplier)}"' not in detail_html(client, supplier)

    supplier.archive()
    assert f'action="{restore_url(supplier)}"' not in detail_html(client, supplier)


@pytest.mark.django_db
def test_archive_and_restore_controls_are_shown_with_archive_supplier(
    client, business, archivist, supplier
):
    client.force_login(archivist)

    assert f'action="{archive_url(supplier)}"' in detail_html(client, supplier)

    supplier.archive()
    assert f'action="{restore_url(supplier)}"' in detail_html(client, supplier)

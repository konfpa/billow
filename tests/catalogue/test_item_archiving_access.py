import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from tests.conftest import role


def archive_url(item):
    return reverse("archive_item", args=[item.pk])


def restore_url(item):
    return reverse("restore_item", args=[item.pk])


def detail_html(client, item):
    return client.get(reverse("item_detail", args=[item.pk])).content.decode()


@pytest.mark.django_db
def test_archive_item_is_named_as_the_admin_shows_it():
    permission = Permission.objects.get(
        content_type__app_label="catalogue", codename="archive_item"
    )

    assert permission.name == "Can archive item"


@pytest.mark.django_db
def test_without_archive_item_archiving_is_refused(client, signed_in, item):
    response = client.post(archive_url(item))

    assert response.status_code == 403
    assert "Can archive item" in response.content.decode()
    item.refresh_from_db()
    assert not item.is_archived


@pytest.mark.django_db
def test_without_archive_item_restoring_is_refused(client, signed_in, item):
    item.archive()

    response = client.post(restore_url(item))

    assert response.status_code == 403
    assert "Can archive item" in response.content.decode()
    item.refresh_from_db()
    assert item.is_archived


@pytest.mark.django_db
def test_archive_item_through_a_role_archives_and_restores(
    client, business, powerless, item
):
    powerless.groups.add(role("Archivist", "catalogue.archive_item"))
    client.force_login(powerless)

    assert client.post(archive_url(item)).status_code == 302
    item.refresh_from_db()
    assert item.is_archived

    assert client.post(restore_url(item)).status_code == 302
    item.refresh_from_db()
    assert not item.is_archived


@pytest.mark.django_db
def test_archiving_requires_signing_in(client, business, item):
    url = archive_url(item)

    response = client.post(url)

    item.refresh_from_db()
    assert response.url == f"{reverse('login')}?next={url}"
    assert not item.is_archived


@pytest.mark.django_db
def test_the_setup_gate_holds_archiving_shut(client, superuser, item):
    client.force_login(superuser)

    response = client.post(archive_url(item))

    item.refresh_from_db()
    assert response.status_code == 302
    assert not item.is_archived


@pytest.mark.django_db
def test_archive_and_restore_controls_are_hidden_without_archive_item(
    client, signed_in, item
):
    assert f'action="{archive_url(item)}"' not in detail_html(client, item)

    item.archive()
    assert f'action="{restore_url(item)}"' not in detail_html(client, item)


@pytest.mark.django_db
def test_archive_and_restore_controls_are_shown_with_archive_item(
    client, signed_in, item
):
    signed_in.groups.add(role("Archivist", "catalogue.archive_item"))

    assert f'action="{archive_url(item)}"' in detail_html(client, item)

    item.archive()
    assert f'action="{restore_url(item)}"' in detail_html(client, item)

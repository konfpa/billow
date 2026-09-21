import pytest
from django.urls import reverse

from apps.catalogue.models import Item
from tests.catalogue.conftest import submitted
from tests.conftest import role

DIRECTORY = reverse("item_directory")
RECORD = reverse("record_item")
HOME = reverse("home")


def reading_pages(item):
    return [DIRECTORY, reverse("item_detail", args=[item.pk])]


@pytest.mark.django_db
def test_without_view_item_every_item_page_is_refused(
    client, business, powerless, item
):
    client.force_login(powerless)

    for url in reading_pages(item):
        response = client.get(url)

        assert response.status_code == 403, url
        assert "Can view item" in response.content.decode()


@pytest.mark.django_db
def test_view_item_through_a_role_opens_every_item_page(
    client, business, powerless, item
):
    powerless.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(powerless)

    for url in reading_pages(item):
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_without_add_item_recording_is_refused(client, business, powerless):
    powerless.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(powerless)

    for response in (client.get(RECORD), client.post(RECORD, submitted())):
        assert response.status_code == 403
        assert "Can add item" in response.content.decode()

    assert not Item.objects.exists()


@pytest.mark.django_db
def test_add_item_through_a_role_records_an_item(client, business, powerless):
    powerless.groups.add(role("Recorder", "catalogue.add_item"))
    client.force_login(powerless)

    assert client.get(RECORD).status_code == 200
    assert client.post(RECORD, submitted()).status_code == 302
    assert Item.objects.exists()


@pytest.mark.django_db
def test_a_superuser_with_no_role_opens_every_item_page(
    client, business, superuser, item
):
    client.force_login(superuser)

    for url in [*reading_pages(item), RECORD]:
        assert client.get(url).status_code == 200, url


@pytest.mark.django_db
def test_the_items_link_is_hidden_without_view_item(client, business, powerless):
    client.force_login(powerless)

    page = client.get(HOME).content.decode()

    assert 'data-tip="Items"' not in page


@pytest.mark.django_db
def test_the_record_control_is_hidden_without_add_item(client, business, powerless):
    powerless.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(powerless)

    page = client.get(DIRECTORY).content.decode()

    assert f'href="{RECORD}"' not in page


@pytest.mark.django_db
def test_the_record_control_is_shown_with_add_item(client, signed_in):
    page = client.get(DIRECTORY).content.decode()

    assert '<i data-lucide="plus" class="size-4"></i>New Item' in page

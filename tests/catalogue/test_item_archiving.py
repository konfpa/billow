import pytest
from django.urls import reverse

from apps.catalogue import urls
from apps.catalogue.models import Brand, Category, Item
from tests.catalogue.conftest import record, submitted
from tests.conftest import role

DIRECTORY = reverse("item_directory")
ARCHIVED = f"{DIRECTORY}?show=archived"


def archive_url(item):
    return reverse("archive_item", args=[item.pk])


def restore_url(item):
    return reverse("restore_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


@pytest.fixture
def archivist(signed_in):
    signed_in.groups.add(role("Archivist", "catalogue.archive_item"))
    return signed_in


@pytest.fixture
def archived(item):
    item.archive()
    return item


@pytest.mark.django_db
def test_an_operator_archives_an_item_and_the_row_remains(client, archivist, item):
    response = client.post(archive_url(item), follow=True)

    item.refresh_from_db()
    assert response.status_code == 200
    assert Item.including_archived.count() == 1
    assert item.is_archived


@pytest.mark.django_db
def test_an_archived_item_is_absent_from_the_directory(client, signed_in, archived):
    page = client.get(DIRECTORY).content.decode()

    assert "Jaquar Florentine tap, chrome" not in page


@pytest.mark.django_db
def test_an_archived_item_is_visible_under_a_deliberate_filter(
    client, signed_in, archived
):
    page = client.get(ARCHIVED).content.decode()

    assert "Jaquar Florentine tap, chrome" in page
    assert detail_url(archived) in page


@pytest.mark.django_db
def test_an_item_on_file_is_absent_from_the_archived_filter(client, signed_in, item):
    page = client.get(ARCHIVED).content.decode()

    assert "Jaquar Florentine tap, chrome" not in page


@pytest.mark.django_db
def test_the_archived_filter_is_searched_within(client, signed_in, archived):
    record(name="Astral elbow").archive()

    page = client.get(f"{ARCHIVED}&q=elbow").content.decode()

    assert "Astral elbow" in page
    assert "Jaquar Florentine tap, chrome" not in page


@pytest.mark.django_db
def test_a_search_of_the_directory_leaves_out_the_archived(client, signed_in, archived):
    page = client.get(f"{DIRECTORY}?q=florentine").content.decode()

    assert "No Item matches" in page


@pytest.mark.django_db
def test_the_archived_filter_says_when_nothing_is_archived(client, signed_in, item):
    page = client.get(ARCHIVED).content.decode()

    assert "Nothing archived" in page


@pytest.mark.django_db
def test_the_directory_offers_the_archived_filter(client, signed_in, item):
    page = client.get(DIRECTORY).content.decode()

    assert "show=archived" in page


@pytest.mark.django_db
def test_an_archived_item_is_still_shown_on_its_own_page(client, signed_in, archived):
    page = client.get(detail_url(archived)).content.decode()

    assert "Jaquar Florentine tap, chrome" in page
    assert "Archived on" in page


@pytest.mark.django_db
def test_an_operator_restores_an_archived_item(client, archivist, archived):
    client.post(restore_url(archived))

    archived.refresh_from_db()
    assert not archived.is_archived


@pytest.mark.django_db
def test_a_restored_item_is_the_same_item(client, archivist, archived):
    pk, code = archived.pk, archived.code

    client.post(restore_url(archived))

    restored = Item.objects.get()
    assert (restored.pk, restored.code) == (pk, code)
    assert restored.stock_unit.selling_price == archived.stock_unit.selling_price


@pytest.mark.django_db
def test_a_restored_item_returns_to_the_directory(client, archivist, archived):
    client.post(restore_url(archived))

    page = client.get(DIRECTORY).content.decode()
    assert "Jaquar Florentine tap, chrome" in page


@pytest.mark.django_db
def test_archiving_names_the_operator_who_did_it(client, archivist, item):
    client.post(archive_url(item))

    latest = item.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == archivist
    assert latest.archived_at is not None


@pytest.mark.django_db
def test_restoring_names_the_operator_who_did_it(client, archivist, archived):
    client.post(restore_url(archived))

    latest = archived.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == archivist
    assert latest.archived_at is None


@pytest.mark.django_db
def test_archiving_returns_to_the_item_and_is_confirmed(client, archivist, item):
    response = client.post(archive_url(item), follow=True)

    assert response.redirect_chain[-1][0] == detail_url(item)
    assert "Jaquar Florentine tap, chrome is archived." in response.content.decode()


@pytest.mark.django_db
def test_restoring_returns_to_the_item_and_is_confirmed(client, archivist, archived):
    response = client.post(restore_url(archived), follow=True)

    assert response.redirect_chain[-1][0] == detail_url(archived)
    assert "Jaquar Florentine tap, chrome is back on file." in response.content.decode()


@pytest.mark.django_db
def test_an_item_on_file_is_offered_archiving(client, archivist, item):
    page = client.get(detail_url(item)).content.decode()

    assert archive_url(item) in page
    assert restore_url(item) not in page


@pytest.mark.django_db
def test_an_archived_item_is_offered_restoring(client, archivist, archived):
    page = client.get(detail_url(archived)).content.decode()

    assert restore_url(archived) in page
    assert archive_url(archived) not in page


def test_nothing_in_the_catalogue_deletes_an_item():
    """Archiving is the only withdrawal there is; see docs/adr/0008."""
    assert not any("delete" in (pattern.name or "") for pattern in urls.urlpatterns)


@pytest.mark.django_db
def test_archiving_an_archived_item_leaves_it_as_it_was(client, archivist, archived):
    archived_at = archived.archived_at

    client.post(archive_url(archived))

    archived.refresh_from_db()
    assert archived.archived_at == archived_at
    assert archived.history.count() == 2


@pytest.mark.django_db
def test_restoring_an_item_on_file_leaves_it_as_it_was(client, archivist, item):
    client.post(restore_url(item))

    item.refresh_from_db()
    assert not item.is_archived
    assert item.history.count() == 1


@pytest.mark.django_db
def test_an_archived_item_is_still_corrected(client, signed_in, archived):
    client.post(
        reverse("edit_item", args=[archived.pk]), submitted(name="Florentine tap")
    )

    archived.refresh_from_db()
    assert archived.name == "Florentine tap"
    assert archived.is_archived


@pytest.mark.django_db
def test_archiving_is_only_a_post(client, archivist, item):
    response = client.get(archive_url(item))

    item.refresh_from_db()
    assert response.status_code == 405
    assert not item.is_archived


@pytest.mark.django_db
def test_an_item_that_is_not_on_file_is_not_found(client, archivist):
    response = client.post(reverse("archive_item", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_code_an_archived_item_holds_says_it_is_archived(client, signed_in, archived):
    page = client.post(
        reverse("record_item"), submitted(name="New tap", code=archived.code)
    ).content.decode()

    assert Item.including_archived.count() == 1
    assert "Jaquar Florentine tap, chrome already holds this Item code." in page
    assert "It is archived, and can be restored." in page


@pytest.mark.django_db
def test_an_archived_item_still_counts_for_the_next_code(client, signed_in):
    record(name="Old tap", code="I-0041").archive()

    client.post(reverse("record_item"), submitted(name="New tap"))

    assert Item.objects.get(name="New tap").code == "I-0042"


@pytest.mark.django_db
def test_a_brand_counts_only_the_items_on_file(client, signed_in, storekeeper):
    storekeeper.groups.add(role("Brands", "catalogue.view_brand"))
    jaquar = Brand.objects.create(name="Jaquar")
    record(brand=jaquar)
    record(name="Old tap", brand=jaquar).archive()

    response = client.get(reverse("brand_directory"))

    assert [brand.item_count for brand in response.context["brands"]] == [1]


@pytest.mark.django_db
def test_a_category_counts_only_the_items_on_file(client, signed_in, storekeeper):
    storekeeper.groups.add(role("Categories", "catalogue.view_category"))
    taps = Category.objects.create(name="Taps")
    record(category=taps)
    record(name="Old tap", category=taps).archive()

    response = client.get(reverse("category_directory"))

    assert [category.item_count for category in response.context["categories"]] == [1]


@pytest.mark.django_db
def test_the_default_manager_leaves_out_the_archived(archived):
    assert not Item.objects.exists()
    assert Item.including_archived.get() == archived
    assert list(Item.including_archived.archived()) == [archived]


@pytest.mark.django_db
def test_an_archived_item_is_still_duplicated(client, signed_in, archived):
    client.post(
        reverse("duplicate_item", args=[archived.pk]), submitted(name="Black tap")
    )

    assert not Item.objects.get(name="Black tap").is_archived

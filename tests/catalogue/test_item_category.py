import json

import pytest
from django.urls import reverse

from apps.catalogue.models import Brand, Category, Item
from tests.catalogue.conftest import record, submitted
from tests.conftest import role

RECORD = reverse("record_item")
DIRECTORY = reverse("item_directory")


def edit_url(item):
    return reverse("edit_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


def names(response):
    return [item.name for item in response.context["items"]]


@pytest.fixture
def fittings(db):
    return Category.objects.create(name="Fittings")


@pytest.fixture
def elbow(fittings):
    return Category.objects.create(name="Elbow", parent=fittings)


@pytest.fixture
def may_add_categories(signed_in):
    signed_in.groups.add(role("Category keeper", "catalogue.add_category"))
    return signed_in


@pytest.mark.django_db
def test_an_operator_gives_an_item_a_category(client, signed_in, elbow):
    client.post(RECORD, submitted(category=str(elbow.pk)))

    assert Item.objects.get().category == elbow


@pytest.mark.django_db
def test_a_category_is_optional(client, signed_in):
    client.post(RECORD, submitted())

    assert Item.objects.get().category is None


@pytest.mark.django_db
def test_an_operator_changes_an_items_category(client, signed_in, item, elbow):
    client.post(edit_url(item), submitted(category=str(elbow.pk)))

    item.refresh_from_db()
    assert item.category == elbow


@pytest.mark.django_db
def test_an_operator_takes_an_items_category_away(client, signed_in, elbow):
    item = record(category=elbow)

    client.post(edit_url(item), submitted(category=""))

    item.refresh_from_db()
    assert item.category is None


@pytest.mark.django_db
def test_the_form_offers_every_category_by_its_path(client, signed_in, elbow):
    page = client.get(RECORD).content.decode()

    options = page.split('id="category-options" type="application/json">')[1]
    options = json.loads(options.split("</script>")[0])
    assert [option["name"] for option in options] == ["Fittings", "Fittings › Elbow"]


@pytest.mark.django_db
def test_the_edit_form_arrives_with_the_category_on_file(client, signed_in, elbow):
    item = record(category=elbow)

    form = client.get(edit_url(item)).context["form"]

    assert form["category"].value() == elbow.pk


@pytest.mark.django_db
def test_a_category_typed_while_recording_is_created_with_the_item(
    client, may_add_categories
):
    client.post(RECORD, submitted(category_new="  Fittings "))

    category = Category.objects.get()
    assert category.name == "Fittings"
    assert category.parent is None
    assert Item.objects.get().category == category


@pytest.mark.django_db
@pytest.mark.parametrize("typed", ["Fittings › Tee", "fittings > Tee", "Fittings>Tee"])
def test_a_category_typed_under_one_on_file_is_created_there(
    client, may_add_categories, fittings, typed
):
    client.post(RECORD, submitted(category_new=typed))

    category = Item.objects.get().category
    assert category.name == "Tee"
    assert category.parent == fittings
    assert Category.objects.count() == 2


@pytest.mark.django_db
def test_a_category_typed_under_a_new_one_creates_both(
    client, may_add_categories, item
):
    client.post(edit_url(item), submitted(category_new="Pipes › PVC"))

    item.refresh_from_db()
    assert str(item.category) == "Pipes › PVC"
    assert item.category.parent.parent is None


@pytest.mark.django_db
def test_a_category_typed_three_levels_deep_is_refused(client, may_add_categories):
    response = client.post(
        RECORD, submitted(category_new="Fittings › Elbow › Threaded")
    )

    assert not Item.objects.exists()
    assert not Category.objects.exists()
    assert response.context["form"].errors["category"] == [
        "Categories go only two levels deep, such as Fittings › Elbow."
    ]


@pytest.mark.django_db
def test_a_typed_category_already_on_file_is_refused(client, may_add_categories, elbow):
    response = client.post(RECORD, submitted(category_new="FITTINGS › elbow"))

    assert not Item.objects.exists()
    assert Category.objects.count() == 2
    assert response.context["form"].errors["category"] == [
        "Fittings › Elbow is already a Category."
    ]


@pytest.mark.django_db
def test_a_typed_category_needs_add_category(client, signed_in):
    response = client.post(RECORD, submitted(category_new="Fittings"))

    assert not Item.objects.exists()
    assert not Category.objects.exists()
    assert response.context["form"].errors["category"] == [
        "Adding a Category needs the permission “Can add category”."
    ]


@pytest.mark.django_db
def test_a_refused_item_keeps_the_category_typed_for_it(client, may_add_categories):
    response = client.post(RECORD, submitted(name="", category_new="Pipes › PVC"))

    assert not Category.objects.exists()
    assert response.context["form"]["category_new"].value() == "Pipes › PVC"


@pytest.mark.django_db
def test_the_form_offers_to_create_a_category_only_with_add_category(client, signed_in):
    def offered():
        page = client.get(RECORD).content.decode()
        return page.split('x-data="picker"')[2].split(">")[0]

    assert 'data-can-create="false"' in offered()
    signed_in.groups.add(role("Category keeper", "catalogue.add_category"))
    client.force_login(signed_in)
    assert 'data-can-create="true"' in offered()


@pytest.mark.django_db
def test_the_detail_page_shows_the_category_as_parent_and_child(
    client, signed_in, elbow
):
    item = record(category=elbow)

    assert "Fittings › Elbow" in client.get(detail_url(item)).content.decode()


@pytest.mark.django_db
def test_the_detail_page_says_when_there_is_no_category(client, signed_in, item):
    assert "No Category" in client.get(detail_url(item)).content.decode()


@pytest.mark.django_db
def test_filtering_by_a_top_level_category_includes_its_children(
    client, signed_in, fittings, elbow
):
    record(name="Plain elbow", category=elbow)
    record(name="Fitting kit", category=fittings)
    record(name="PVC pipe", category=Category.objects.create(name="Pipes"))
    record(name="Plain washer")

    response = client.get(DIRECTORY, {"category": fittings.pk})

    assert names(response) == ["Fitting kit", "Plain elbow"]
    page = response.content.decode()
    assert "2 of 4 on file in Fittings" in page
    assert f'<option value="{fittings.pk}" selected>Fittings</option>' in page


@pytest.mark.django_db
def test_filtering_by_a_child_category_shows_only_its_items(
    client, signed_in, fittings, elbow
):
    record(name="Plain elbow", category=elbow)
    record(
        name="Plain tee", category=Category.objects.create(name="Tee", parent=fittings)
    )
    record(name="Fitting kit", category=fittings)

    response = client.get(DIRECTORY, {"category": elbow.pk})

    assert names(response) == ["Plain elbow"]
    assert (
        f'<option value="{elbow.pk}" selected>Fittings › Elbow</option>'
        in response.content.decode()
    )


@pytest.mark.django_db
def test_the_category_and_brand_filters_combine(client, signed_in, fittings, elbow):
    jaquar = Brand.objects.create(name="Jaquar")
    record(name="Jaquar elbow", category=elbow, brand=jaquar)
    record(name="Plain elbow", category=elbow)
    record(name="Jaquar tap", brand=jaquar)

    response = client.get(DIRECTORY, {"category": fittings.pk, "brand": jaquar.pk})

    assert names(response) == ["Jaquar elbow"]
    assert "1 of 3 on file from Jaquar in Fittings" in response.content.decode()


@pytest.mark.django_db
def test_a_category_with_no_items_says_so(client, signed_in, fittings):
    record(name="Plain washer")

    page = client.get(DIRECTORY, {"category": fittings.pk}).content.decode()

    assert "No Items in Fittings" in page
    assert f'href="{DIRECTORY}"' in page


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["9999", "fittings"])
def test_an_unknown_category_filter_is_ignored(client, signed_in, item, category):
    response = client.get(DIRECTORY, {"category": category})

    assert list(response.context["items"]) == [item]


@pytest.mark.django_db
def test_an_items_history_records_its_category(client, signed_in, item, elbow):
    client.post(edit_url(item), submitted(category=str(elbow.pk)))

    assert item.history.first().category_id == elbow.pk


@pytest.mark.django_db
def test_a_category_typed_under_a_child_is_refused(client, may_add_categories, elbow):
    response = client.post(RECORD, submitted(category_new="Elbow › Threaded"))

    assert not Item.objects.exists()
    assert Category.objects.count() == 2
    assert response.context["form"].errors["category"] == [
        "Elbow is already under Fittings, and Categories go only two levels deep."
    ]

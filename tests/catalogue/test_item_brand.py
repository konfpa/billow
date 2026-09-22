import json

import pytest
from django.urls import reverse

from apps.catalogue.models import Brand, Item
from tests.catalogue.conftest import record, submitted
from tests.conftest import role

RECORD = reverse("record_item")
DIRECTORY = reverse("item_directory")


def edit_url(item):
    return reverse("edit_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


@pytest.fixture
def jaquar(db):
    return Brand.objects.create(name="Jaquar")


@pytest.fixture
def may_add_brands(signed_in):
    signed_in.groups.add(role("Brand keeper", "catalogue.add_brand"))
    return signed_in


@pytest.mark.django_db
def test_an_operator_gives_an_item_a_brand(client, signed_in, jaquar):
    client.post(RECORD, submitted(brand=str(jaquar.pk)))

    assert Item.objects.get().brand == jaquar


@pytest.mark.django_db
def test_a_brand_is_optional(client, signed_in):
    client.post(RECORD, submitted())

    assert Item.objects.get().brand is None


@pytest.mark.django_db
def test_an_operator_changes_an_items_brand(client, signed_in, item, jaquar):
    client.post(edit_url(item), submitted(brand=str(jaquar.pk)))

    item.refresh_from_db()
    assert item.brand == jaquar


@pytest.mark.django_db
def test_an_operator_takes_an_items_brand_away(client, signed_in, jaquar):
    item = record(brand=jaquar)

    client.post(edit_url(item), submitted(brand=""))

    item.refresh_from_db()
    assert item.brand is None


@pytest.mark.django_db
def test_the_form_offers_every_brand(client, signed_in, jaquar):
    Brand.objects.create(name="Astral")

    page = client.get(RECORD).content.decode()

    assert "Astral" in page
    assert "Jaquar" in page


@pytest.mark.django_db
def test_the_edit_form_arrives_with_the_brand_on_file(client, signed_in, jaquar):
    item = record(brand=jaquar)

    form = client.get(edit_url(item)).context["form"]

    assert form["brand"].value() == jaquar.pk


@pytest.mark.django_db
def test_a_brand_typed_while_recording_an_item_is_created_with_it(
    client, may_add_brands
):
    client.post(RECORD, submitted(brand_new="  Jaquar "))

    brand = Brand.objects.get()
    assert brand.name == "Jaquar"
    assert Item.objects.get().brand == brand


@pytest.mark.django_db
def test_a_brand_typed_while_editing_an_item_is_created_with_it(
    client, may_add_brands, item
):
    client.post(edit_url(item), submitted(brand_new="Jaquar"))

    item.refresh_from_db()
    assert item.brand.name == "Jaquar"


@pytest.mark.django_db
def test_a_typed_brand_matching_another_regardless_of_case_is_refused(
    client, may_add_brands, jaquar
):
    response = client.post(RECORD, submitted(brand_new="JAQUAR"))

    assert not Item.objects.exists()
    assert Brand.objects.count() == 1
    assert response.context["form"].errors["brand"] == ["Jaquar is already a Brand."]


@pytest.mark.django_db
def test_a_typed_brand_needs_add_brand(client, signed_in):
    response = client.post(RECORD, submitted(brand_new="Jaquar"))

    assert not Item.objects.exists()
    assert not Brand.objects.exists()
    assert response.context["form"].errors["brand"] == [
        "Adding a Brand needs the permission “Can add brand”."
    ]


@pytest.mark.django_db
def test_a_refused_item_keeps_the_brand_typed_for_it(client, may_add_brands):
    response = client.post(RECORD, submitted(name="", brand_new="Jaquar"))

    assert not Brand.objects.exists()
    assert response.context["form"]["brand_new"].value() == "Jaquar"


@pytest.mark.django_db
def test_the_form_offers_to_create_a_brand_only_with_add_brand(
    client, signed_in, business
):
    def offered():
        page = client.get(RECORD).content.decode()
        return 'data-can-create="true"' in page

    assert not offered()
    signed_in.groups.add(role("Brand keeper", "catalogue.add_brand"))
    client.force_login(signed_in)
    assert offered()


@pytest.mark.django_db
def test_the_brand_options_are_escaped_for_the_page(client, signed_in):
    Brand.objects.create(name="M/s D'Souza </script>")

    page = client.get(RECORD).content.decode()

    assert '</script>"' not in page
    options = page.split('id="brand-options" type="application/json">')[1].split(
        "</script>"
    )[0]
    assert json.loads(options)[0]["name"] == "M/s D'Souza </script>"


@pytest.mark.django_db
def test_the_detail_page_shows_the_brand(client, signed_in, jaquar):
    item = record(brand=jaquar)

    page = client.get(detail_url(item)).content.decode()

    assert "Brand" in page
    assert "Jaquar" in page


@pytest.mark.django_db
def test_the_detail_page_says_when_there_is_no_brand(client, signed_in, item):
    assert "No Brand" in client.get(detail_url(item)).content.decode()


@pytest.mark.django_db
def test_the_directory_filters_by_brand(client, signed_in, jaquar):
    record(name="Jaquar tap", brand=jaquar)
    record(name="Astral pipe", brand=Brand.objects.create(name="Astral"))
    record(name="Plain washer")

    response = client.get(DIRECTORY, {"brand": jaquar.pk})

    assert [item.name for item in response.context["items"]] == ["Jaquar tap"]
    page = response.content.decode()
    assert "1 of 3 on file" in page
    assert f'<option value="{jaquar.pk}" selected>Jaquar</option>' in page


@pytest.mark.django_db
def test_a_brand_with_no_items_says_so(client, signed_in, jaquar):
    record(name="Plain washer")

    response = client.get(DIRECTORY, {"brand": jaquar.pk})

    page = response.content.decode()
    assert "No Items from Jaquar" in page
    assert f'href="{DIRECTORY}"' in page


@pytest.mark.django_db
@pytest.mark.parametrize("brand", ["9999", "jaquar"])
def test_an_unknown_brand_filter_is_ignored(client, signed_in, item, brand):
    response = client.get(DIRECTORY, {"brand": brand})

    assert list(response.context["items"]) == [item]


@pytest.mark.django_db
def test_the_directory_shows_each_items_brand(client, signed_in, jaquar):
    record(name="Jaquar tap", brand=jaquar)

    assert "Jaquar" in client.get(DIRECTORY).content.decode()


@pytest.mark.django_db
def test_an_items_history_records_its_brand(client, signed_in, item, jaquar):
    client.post(edit_url(item), submitted(brand=str(jaquar.pk)))

    assert item.history.first().brand_id == jaquar.pk

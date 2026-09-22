import pytest
from django.urls import reverse

from apps.catalogue.models import Brand, Category
from tests.catalogue.conftest import record

DIRECTORY = reverse("item_directory")


@pytest.fixture
def elbows(db):
    """Three of the forty similar elbows an Operator searches among."""
    fta = Brand.objects.create(name="FTA")
    astral = Brand.objects.create(name="Astral")
    return [
        record(name="Elbow FTA ¾ inch", code="ELB-FTA-075", brand=fta),
        record(name="Elbow FTA 1 inch", code="ELB-FTA-100", brand=fta),
        record(name="Elbow ¾ inch", code="ELB-AST-075", brand=astral),
    ]


def found(client, query, **params):
    response = client.get(DIRECTORY, {"q": query, **params})
    return [item.name for item in response.context["items"]]


@pytest.mark.django_db
def test_fragments_of_the_name_in_any_order_find_the_item(client, signed_in, elbows):
    assert found(client, "elb ¾ fta") == ["Elbow FTA ¾ inch"]


@pytest.mark.django_db
def test_an_item_is_found_only_if_every_word_matches(client, signed_in, elbows):
    assert found(client, "elbow astral ¾") == ["Elbow ¾ inch"]
    assert found(client, "elbow astral fta") == []


@pytest.mark.django_db
def test_part_of_an_item_code_finds_it(client, signed_in, elbows):
    assert found(client, "ast-075") == ["Elbow ¾ inch"]


@pytest.mark.django_db
def test_a_brand_name_finds_its_items(client, signed_in, elbows):
    assert found(client, "astral") == ["Elbow ¾ inch"]


@pytest.mark.django_db
def test_search_combines_with_the_brand_filter(client, signed_in, elbows):
    astral = Brand.objects.get(name="Astral")

    assert found(client, "¾", brand=astral.pk) == ["Elbow ¾ inch"]


@pytest.mark.django_db
def test_search_combines_with_the_category_filter(client, signed_in, elbows):
    fittings = Category.objects.create(name="Fittings")
    elbows[0].category = Category.objects.create(name="Elbow", parent=fittings)
    elbows[0].save()

    assert found(client, "¾", category=fittings.pk) == ["Elbow FTA ¾ inch"]


@pytest.mark.django_db
def test_a_search_matching_nothing_says_so(client, signed_in, elbows):
    page = client.get(DIRECTORY, {"q": "Tee"}).content.decode()

    assert "No Item matches “Tee”" in page
    assert "No Items yet" not in page
    assert "Clear the search" in page


@pytest.mark.django_db
def test_a_search_matching_nothing_keeps_the_filter_to_clear(client, signed_in, elbows):
    astral = Brand.objects.get(name="Astral")

    page = client.get(DIRECTORY, {"q": "FTA", "brand": astral.pk}).content.decode()

    assert "No Item matches “FTA” from Astral" in page
    assert f'href="{DIRECTORY}?brand={astral.pk}"' in page
    assert f'href="{DIRECTORY}?q=FTA"' in page


@pytest.mark.django_db
def test_the_search_box_keeps_what_was_searched(client, signed_in, elbows):
    page = client.get(DIRECTORY, {"q": "astral"}).content.decode()

    assert 'name="q" value="astral"' in page
    assert "1 of 3 on file matches “astral”" in page

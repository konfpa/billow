"""The directory arrives a page at a time, however long the register is."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.pagination import PER_PAGE
from tests.catalogue.conftest import record

DIRECTORY = reverse("item_directory")


@pytest.fixture
def a_page_and_one(db):
    """One Item more than a page holds, each nameable on its own."""
    return [record(name=f"Tap {number:03d}") for number in range(PER_PAGE + 1)]


@pytest.mark.django_db
def test_a_page_holds_no_more_than_a_page(client, signed_in, a_page_and_one):
    response = client.get(DIRECTORY)

    assert len(response.context["items"]) == PER_PAGE


@pytest.mark.django_db
def test_the_rest_are_on_the_next_page(client, signed_in, a_page_and_one):
    response = client.get(DIRECTORY, {"page": "2"})

    assert len(response.context["items"]) == 1


@pytest.mark.django_db
def test_the_count_is_of_everything_on_file_not_of_the_page(
    client, signed_in, a_page_and_one
):
    page = client.get(DIRECTORY).content.decode()

    assert f"{PER_PAGE + 1} on file" in page


@pytest.mark.django_db
def test_a_search_is_carried_onto_the_next_page(client, signed_in, a_page_and_one):
    """Page 2 of a search is page 2 of the search, not of the catalogue."""
    page = client.get(DIRECTORY, {"q": "Tap"}).content.decode()

    assert "q=Tap&amp;page=2" in page


@pytest.mark.django_db
def test_a_page_past_the_end_lands_on_the_last_one(client, signed_in, a_page_and_one):
    """A bookmarked page of a directory that has since shrunk still opens."""
    response = client.get(DIRECTORY, {"page": "98"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 2


@pytest.mark.django_db
def test_the_register_is_never_fetched_whole_to_draw_a_page(
    client, signed_in, a_page_and_one
):
    """The bug this paging exists to fix, and the one easiest to undo.

    Asking a queryset whether it is empty — `if items:` — fetches every row and
    caches them, and the slice that follows is then taken in Python rather than
    by the database. The page still looks right, so nothing catches it but this.
    """
    with CaptureQueriesContext(connection) as queries:
        client.get(DIRECTORY)

    fetched = [
        q["sql"]
        for q in queries.captured_queries
        if '"catalogue_item"' in q["sql"] and "COUNT" not in q["sql"].upper()
    ]
    assert fetched, "the directory asked for no Items at all"
    assert all(f"LIMIT {PER_PAGE}" in sql for sql in fetched), fetched


@pytest.mark.django_db
def test_one_page_of_items_is_not_given_a_pager(client, signed_in, item):
    page = client.get(DIRECTORY).content.decode()

    assert 'data-kui="pagination/links"' not in page

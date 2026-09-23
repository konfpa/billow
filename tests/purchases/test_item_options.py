"""The line picker's search endpoint, which stands in for the catalogue.

The Purchase form carries no Items of its own; these rows are the only copy an
open picker has, so what they carry and who may ask for them is the whole of it.
"""

import pytest
from django.urls import reverse

from apps.purchases.views import OPTIONS_SHOWN
from tests.purchases.conftest import goods

SEARCH = reverse("item_options")


@pytest.mark.django_db
def test_a_search_answers_with_no_more_than_a_pickers_worth(client, signed_in):
    for number in range(OPTIONS_SHOWN + 5):
        goods(f"Tap {number:03d}", f"TAP-{number:03d}")

    rows = client.get(SEARCH, {"q": "Tap"}).content.decode()

    assert rows.count('role="option"') == OPTIONS_SHOWN


@pytest.mark.django_db
def test_every_word_has_to_match(client, signed_in, elbow):
    """As the directory's search does: "elb ¾" narrows, it does not widen."""
    assert "ELB-075" in client.get(SEARCH, {"q": "CPVC ¾"}).content.decode()
    assert "ELB-075" not in client.get(SEARCH, {"q": "CPVC brass"}).content.decode()


@pytest.mark.django_db
def test_a_name_with_a_quote_in_it_cannot_break_out_of_its_row(client, signed_in):
    """The name is an attribute value, and an Item is named by whoever types it."""
    goods('Tap 1" brass <script>', "TAP-Q")

    rows = client.get(SEARCH, {"q": "brass"}).content.decode()

    assert "<script>" not in rows
    assert 'data-label="Tap 1&quot; brass &lt;script&gt;"' in rows


@pytest.mark.django_db
def test_the_search_is_refused_without_permission_to_record(
    client, business, powerless
):
    """The catalogue is not readable by asking the picker for it."""
    client.force_login(powerless)

    assert client.get(SEARCH, {"q": "Tap"}).status_code == 403


@pytest.mark.django_db
def test_the_search_is_refused_when_signed_out(client, business):
    response = client.get(SEARCH, {"q": "Tap"})

    assert response.status_code == 302
    assert "/sign-in/" in response.url

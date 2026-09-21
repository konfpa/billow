import pytest
from django.urls import reverse

from apps.tax.rates import GSTRate
from tests.catalogue.conftest import record

DIRECTORY = reverse("item_directory")


@pytest.mark.django_db
def test_the_directory_lists_each_item_with_code_unit_price_and_rate(
    client, signed_in, item
):
    page = client.get(DIRECTORY).content.decode()

    assert "Jaquar Florentine tap, chrome" in page
    assert "I-0001" in page
    assert "NOS" in page
    assert "₹1450.00" in page
    assert "18%" in page


@pytest.mark.django_db
def test_the_directory_is_in_name_order(client, signed_in):
    record(name="Union elbow ¾ inch")
    record(name="Ball valve ½ inch")
    record(name="PVC pipe 1 inch")

    items = list(client.get(DIRECTORY).context["items"])

    assert [item.name for item in items] == [
        "Ball valve ½ inch",
        "PVC pipe 1 inch",
        "Union elbow ¾ inch",
    ]


@pytest.mark.django_db
def test_an_item_without_a_price_says_so(client, signed_in):
    record(name="Tap fitting", price=None, gst_rate=GSTRate.EIGHTEEN)

    page = client.get(DIRECTORY).content.decode()

    assert "No price" in page


@pytest.mark.django_db
def test_an_empty_directory_says_nothing_is_on_file(client, signed_in):
    page = client.get(DIRECTORY).content.decode()

    assert "No Items yet" in page


@pytest.mark.django_db
def test_every_row_leads_to_the_item(client, signed_in, item):
    page = client.get(DIRECTORY).content.decode()

    detail = reverse("item_detail", args=[item.pk])
    assert page.count(f'href="{detail}"') == 2


@pytest.mark.django_db
def test_the_directory_counts_the_items_on_file(client, signed_in):
    record(name="Chrome tap")
    record(name="Black tap")

    page = client.get(DIRECTORY).content.decode()

    assert "2 on file" in page


@pytest.mark.django_db
def test_the_directory_requires_signing_in(client, business):
    response = client.get(DIRECTORY)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={DIRECTORY}"


@pytest.mark.django_db
def test_the_directory_is_reachable_from_every_page(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert f'href="{DIRECTORY}"' in home
    assert 'data-tip="Items"' in home

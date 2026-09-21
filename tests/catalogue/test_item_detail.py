import pytest
from django.urls import reverse

from apps.catalogue.models import Item
from tests.catalogue.conftest import record

DIRECTORY = reverse("item_directory")


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


@pytest.mark.django_db
def test_every_detail_of_an_item_is_shown(client, signed_in, item):
    response = client.get(detail_url(item))

    assert response.status_code == 200
    page = response.content.decode()
    for detail in (
        "Jaquar Florentine tap, chrome",
        "I-0001",
        "Goods",
        "848180",
        "18%",
        "NOS · Numbers",
        "₹1450.00",
    ):
        assert detail in page, detail


@pytest.mark.django_db
def test_a_service_is_shown_with_its_sac(client, signed_in):
    service = record(
        name="Tap fitting", kind=Item.Kind.SERVICE, hsn_sac="995461", price="300"
    )

    page = client.get(detail_url(service)).content.decode()

    assert "Service" in page
    assert "995461" in page
    assert "SAC" in page


@pytest.mark.django_db
def test_an_item_without_a_price_says_so(client, signed_in):
    unpriced = record(price=None)

    page = client.get(detail_url(unpriced)).content.decode()

    assert "No price" in page


@pytest.mark.django_db
def test_an_item_not_on_file_is_not_found(client, signed_in):
    assert client.get(reverse("item_detail", args=[404])).status_code == 404


@pytest.mark.django_db
def test_the_back_link_returns_to_the_directory(client, signed_in, item):
    page = client.get(detail_url(item)).content.decode()

    assert f'href="{DIRECTORY}"' in page


@pytest.mark.django_db
def test_viewing_requires_signing_in(client, business, item):
    url = detail_url(item)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"

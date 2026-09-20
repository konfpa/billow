import pytest
from django.urls import reverse


@pytest.fixture
def change_url(business):
    return reverse("admin:business_business_change", args=[business.pk])


@pytest.mark.django_db
def test_the_admin_shows_the_business(client, superuser, business, change_url):
    client.force_login(superuser)

    response = client.get(change_url)

    assert response.status_code == 200
    assert "Umbrella Trading" in response.content.decode()


@pytest.mark.django_db
def test_the_admin_offers_no_way_to_change_it(client, superuser, business, change_url):
    client.force_login(superuser)

    page = client.get(change_url).content.decode()

    assert 'name="_save"' not in page
    assert '<input type="text" name="name"' not in page


@pytest.mark.django_db
def test_a_change_posted_to_the_admin_is_not_made(
    client, superuser, business, change_url
):
    client.force_login(superuser)

    client.post(change_url, {"name": "Someone Else Trading", "_save": ""})

    business.refresh_from_db()
    assert business.name == "Umbrella Trading"


@pytest.mark.django_db
def test_the_admin_cannot_add_a_second_business(client, superuser, business):
    client.force_login(superuser)

    response = client.get(reverse("admin:business_business_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_the_admin_shows_who_changed_what(client, superuser, business):
    business._history_user = superuser  # noqa: SLF001 — simple_history's documented hook
    business.name = "Umbrella Supplies"
    business.save()
    client.force_login(superuser)

    page = client.get(
        reverse("admin:business_business_history", args=[business.pk]),
    ).content.decode()

    assert page.count("Priya Nair") >= 1

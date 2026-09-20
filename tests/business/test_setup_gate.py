import pytest
from django.urls import reverse

from apps.business.models import Business
from apps.business.states import State
from tests.business.conftest import PASSWORD

HOME = reverse("home")
SETTINGS = reverse("business_settings")


@pytest.fixture
def half_a_business(db):
    """A Business whose setup was never finished."""
    return Business.objects.create(name="Umbrella Trading", state=State.MAHARASHTRA)


@pytest.fixture
def upgraded(business, monkeypatch):
    """A complete Business, and then a release that requires one field more."""
    monkeypatch.setattr(
        Business,
        "REQUIRED_FOR_SETUP",
        (*Business.REQUIRED_FOR_SETUP, "cin"),
    )
    business.cin = ""
    business.save()
    return business


@pytest.mark.django_db
def test_an_unconfigured_billow_sends_every_request_to_setup(client, superuser):
    client.force_login(superuser)

    response = client.get(HOME)

    assert response.status_code == 302
    assert response.url == SETTINGS


@pytest.mark.django_db
@pytest.mark.urls("tests.business.urls_with_a_new_view")
def test_a_view_does_not_have_to_opt_into_the_gate(client, superuser):
    client.force_login(superuser)

    response = client.get("/a-new-view/")

    assert response.status_code == 302
    assert response.url == SETTINGS


@pytest.mark.django_db
def test_signing_in_stays_reachable_while_the_gate_is_closed(client, superuser):
    assert client.get(reverse("login")).status_code == 200

    response = client.post(
        reverse("login"),
        {"username": superuser.email, "password": PASSWORD},
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_signing_out_stays_reachable_while_the_gate_is_closed(client, superuser):
    client.force_login(superuser)

    response = client.post(reverse("logout"))

    assert response.url == reverse("login")


@pytest.mark.django_db
def test_the_admin_stays_reachable_while_the_gate_is_closed(client, superuser):
    client.force_login(superuser)

    response = client.get("/admin/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_the_health_check_stays_reachable_while_the_gate_is_closed(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.urls("tests.business.urls_serving_files")
def test_static_and_media_stay_reachable_while_the_gate_is_closed(
    client, superuser, settings, tmp_path
):
    # Both files are written here rather than taken from the working tree,
    # where the stylesheet is a Tailwind build artifact a fresh clone lacks.
    stylesheets = tmp_path / "static"
    stylesheets.mkdir()
    (stylesheets / "app.css").write_text("body {}")
    settings.STATICFILES_DIRS = [stylesheets]
    (settings.MEDIA_ROOT / "logo.png").write_bytes(b"a logo")
    client.force_login(superuser)

    static = client.get("/static/app.css")
    media = client.get("/media/logo.png")

    assert static.status_code == 200
    assert media.status_code == 200


@pytest.mark.django_db
def test_the_setup_page_names_what_is_missing(client, superuser, half_a_business):
    client.force_login(superuser)

    response = client.get(SETTINGS)

    assert set(response.context["missing"]) == {
        "Address line 1",
        "City",
        "Postal code",
        "GST registered",
    }
    assert "City" in response.content.decode()


@pytest.mark.django_db
def test_the_gate_opens_once_the_required_fields_are_supplied(
    client, superuser, business
):
    client.force_login(superuser)

    assert client.get(HOME).status_code == 200


@pytest.mark.django_db
def test_a_newly_required_field_closes_the_gate_again(client, superuser, upgraded):
    client.force_login(superuser)

    response = client.get(HOME)

    assert response.status_code == 302
    assert response.url == SETTINGS


@pytest.mark.django_db
def test_reopening_asks_only_for_what_an_upgrade_added(client, superuser, upgraded):
    client.force_login(superuser)

    response = client.get(SETTINGS)
    page = response.content.decode()

    assert response.context["missing"] == ["CIN"]
    assert "Umbrella Trading" in page
    assert "14 Marine Drive" in page
    assert "27AAPFU0939F1ZV" in page


@pytest.mark.django_db
def test_an_operator_who_cannot_set_billow_up_is_told_so(client, operator):
    client.force_login(operator)

    response = client.get(HOME)

    assert response.status_code == 200
    assert "needs setting up" in response.content.decode()
    assert "Superuser" in response.content.decode()


@pytest.mark.django_db
def test_nobody_signed_in_is_sent_to_sign_in_rather_than_to_setup(client):
    response = client.get(HOME)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={HOME}"


@pytest.mark.django_db
def test_an_operator_who_cannot_set_billow_up_is_refused_the_setup_page(
    client, operator
):
    client.force_login(operator)

    assert client.get(SETTINGS).status_code == 403


@pytest.mark.django_db
def test_the_setup_page_becomes_the_settings_page_once_the_gate_opens(
    client, superuser, business
):
    client.force_login(superuser)

    page = client.get(SETTINGS).content.decode()

    assert "Settings" in page
    assert "Umbrella Trading" in page

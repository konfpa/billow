import pytest
from django.urls import reverse

from apps.business.models import Business
from tests.business.conftest import submitted
from tests.conftest import role

URL = reverse("business_settings")
HOME = reverse("home")
NAV_LINK = 'data-tip="Business"'
# The logout form is on every page, so the Business form is told apart by its upload.
FORM = 'enctype="multipart/form-data"'


@pytest.fixture
def reader(powerless):
    """A User who may read the Business and do nothing else with it."""
    powerless.groups.add(role("Reader", "business.view_business"))
    return powerless


@pytest.fixture
def editor(reader):
    """A User who may read the Business and change it."""
    reader.groups.add(role("Editor", "business.change_business"))
    return reader


@pytest.mark.django_db
def test_without_view_business_the_settings_are_refused(client, business, powerless):
    client.force_login(powerless)

    response = client.get(URL)

    assert response.status_code == 403
    assert "Can view business" in response.content.decode()


@pytest.mark.django_db
def test_view_business_alone_shows_the_details_without_the_form(
    client, business, reader
):
    client.force_login(reader)

    response = client.get(URL)

    assert response.status_code == 200
    assert "Umbrella Trading" in response.content.decode()
    assert FORM not in response.content.decode()


@pytest.mark.django_db
def test_without_change_business_a_save_is_refused(client, business, reader):
    client.force_login(reader)

    response = client.post(URL, submitted(name="Someone Else Trading"))

    assert response.status_code == 403
    assert "Can change business" in response.content.decode()
    assert Business.objects.get().name == "Umbrella Trading"


@pytest.mark.django_db
def test_change_business_alone_is_not_enough_to_save(client, business, powerless):
    powerless.groups.add(role("Editor", "business.change_business"))
    client.force_login(powerless)

    response = client.post(URL, submitted(name="Someone Else Trading"))

    assert response.status_code == 403
    assert "Can view business" in response.content.decode()
    assert Business.objects.get().name == "Umbrella Trading"


@pytest.mark.django_db
def test_view_and_change_business_through_roles_edit_the_business(
    client, business, editor
):
    client.force_login(editor)

    assert FORM in client.get(URL).content.decode()
    response = client.post(URL, submitted(name="Umbrella Supplies"))

    assert response.status_code == 302
    assert Business.objects.get().name == "Umbrella Supplies"


@pytest.mark.django_db
def test_the_business_link_is_absent_without_view_business(client, business, powerless):
    client.force_login(powerless)

    assert NAV_LINK not in client.get(HOME).content.decode()


@pytest.mark.django_db
def test_the_business_link_is_present_with_view_business(client, business, reader):
    client.force_login(reader)

    assert NAV_LINK in client.get(HOME).content.decode()


@pytest.mark.django_db
def test_while_setting_up_view_and_change_business_are_not_enough(client, editor):
    client.force_login(editor)

    assert client.get(URL).status_code == 403
    response = client.post(URL, submitted())

    assert response.status_code == 403
    assert Business.load().missing_for_setup()

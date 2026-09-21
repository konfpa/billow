import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.business.models import Business
from apps.tax.states import State
from tests.business.conftest import COMPLETE

URL = reverse("business_settings")


def submitted(**changes):
    """What the form posts: the complete Business, with anything changed."""
    posted = {**COMPLETE, "is_gst_registered": "True", **changes}
    return {key: value for key, value in posted.items() if value is not None}


def an_image(name="logo.png"):
    content = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(content, format="PNG")
    return SimpleUploadedFile(name, content.getvalue(), "image/png")


@pytest.mark.django_db
def test_the_page_requires_signing_in(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={URL}"


@pytest.mark.django_db
def test_a_superuser_records_the_business(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(), follow=True)

    assert response.status_code == 200
    business = Business.objects.get()
    assert business.name == "Umbrella Trading"
    assert business.gstin == "27AAPFU0939F1ZV"
    assert business.state == State.MAHARASHTRA
    assert "saved" in response.content.decode()


@pytest.mark.django_db
def test_a_blank_legal_name_is_not_a_copy_of_the_display_name(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(legal_name=""))

    business = Business.objects.get()
    assert business.legal_name == ""
    assert business.invoice_name == "Umbrella Trading"


@pytest.mark.django_db
def test_the_state_is_chosen_from_a_list(client, superuser):
    client.force_login(superuser)

    page = client.get(URL).content.decode()

    assert '<select name="state"' in page
    assert '<option value="27">Maharashtra</option>' in page


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(gstin="27AAPFU0939F1ZW"))

    assert response.status_code == 200
    assert not Business.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_from_another_state_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(state=State.KARNATAKA))

    assert not Business.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_registered_business_must_give_its_gstin(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(gstin=""))

    assert not Business.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_an_unregistered_business_is_recorded_without_a_gstin(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(is_gst_registered="False", gstin=""))

    business = Business.objects.get()
    assert business.is_gst_registered is False
    assert business.gstin == ""


@pytest.mark.django_db
def test_an_unanswered_gst_registration_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(is_gst_registered=None, gstin=""))

    assert not Business.objects.exists()
    assert "is_gst_registered" in response.context["form"].errors


@pytest.mark.django_db
def test_a_refused_submission_keeps_what_was_already_typed(client, superuser):
    client.force_login(superuser)

    page = client.post(URL, submitted(gstin="27AAPFU0939F1ZW")).content.decode()

    assert "Umbrella Trading" in page
    assert "14 Marine Drive" in page
    assert "27AAPFU0939F1ZW" in page


@pytest.mark.django_db
def test_a_gstin_typed_in_lower_case_is_stored_in_capitals(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(gstin="27aapfu0939f1zv"))

    assert Business.objects.get().gstin == "27AAPFU0939F1ZV"


@pytest.mark.django_db
def test_what_setup_requires_is_what_the_form_demands(client, superuser):
    client.force_login(superuser)

    form = client.get(URL).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Business.REQUIRED_FOR_SETUP)


@pytest.mark.django_db
def test_a_logo_is_recorded(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(logo=an_image()))

    assert Business.objects.get().logo


@pytest.mark.django_db
def test_the_logo_is_optional(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted())

    assert not Business.objects.get().logo


@pytest.mark.django_db
def test_a_logo_that_is_not_an_image_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(
        URL,
        submitted(logo=SimpleUploadedFile("logo.png", b"not an image", "image/png")),
    )

    assert not Business.objects.exists()
    assert "logo" in response.context["form"].errors


@pytest.mark.django_db
def test_a_refused_submission_does_not_show_its_logo_as_the_current_one(
    client, superuser, business
):
    business.logo = an_image()
    business.save()
    client.force_login(superuser)

    page = client.post(
        URL,
        submitted(gstin="27AAPFU0939F1ZW", logo=an_image("new-logo.png")),
    ).content.decode()

    assert business.logo.url in page
    assert "new-logo" not in page


@pytest.mark.django_db
def test_a_logo_is_removed_when_the_picker_asks_for_it(client, superuser, business):
    business.logo = an_image()
    business.save()
    client.force_login(superuser)

    client.post(URL, {**submitted(), "logo-clear": "on"})

    assert not Business.objects.get().logo


@pytest.mark.django_db
def test_the_current_logo_is_visible_while_editing(client, superuser, business):
    business.logo = an_image()
    business.save()
    client.force_login(superuser)

    page = client.get(URL).content.decode()

    assert business.logo.url in page


@pytest.mark.django_db
def test_an_operator_who_is_not_a_superuser_may_read_the_business(
    client, operator, business
):
    client.force_login(operator)

    response = client.get(URL)

    assert response.status_code == 200
    assert "Umbrella Trading" in response.content.decode()


@pytest.mark.django_db
def test_an_operator_who_is_not_a_superuser_is_refused_a_change(
    client, operator, business
):
    client.force_login(operator)

    response = client.post(URL, submitted(name="Someone Else Trading"))

    assert response.status_code == 403
    assert Business.objects.get().name == "Umbrella Trading"


@pytest.mark.django_db
def test_a_change_names_the_superuser_who_made_it(client, superuser, business):
    client.force_login(superuser)

    client.post(URL, submitted(name="Umbrella Supplies"))

    assert business.history.latest().history_user == superuser


@pytest.mark.django_db
def test_an_address_keeps_the_lines_it_was_typed_on(client, superuser, operator):
    client.force_login(superuser)
    client.post(
        URL,
        submitted(address="Unit 4, Mistry Chambers\n14 Marine Drive\nNariman Point"),
    )
    client.force_login(operator)

    page = client.get(URL).content.decode()

    assert "Unit 4, Mistry Chambers<br>14 Marine Drive<br>Nariman Point" in page


@pytest.mark.django_db
def test_blank_lines_and_stray_spaces_are_left_out_of_an_address(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(address="  14 Marine Drive  \n\n \nNariman Point\n\n"))

    assert Business.objects.get().address == "14 Marine Drive\nNariman Point"


@pytest.mark.django_db
def test_an_address_of_six_lines_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(address="1\n2\n3\n4\n5\n6"))

    assert not Business.objects.exists()
    assert response.context["form"].errors["address"] == [
        "An address fits on 5 lines or fewer."
    ]


@pytest.mark.django_db
def test_blank_lines_do_not_count_against_an_address(client, superuser):
    client.force_login(superuser)

    client.post(URL, submitted(address="1\n\n2\n\n3\n\n4\n\n5"))

    assert Business.objects.get().address == "1\n2\n3\n4\n5"


@pytest.mark.django_db
def test_an_address_longer_than_500_characters_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(address="x" * 501))

    assert not Business.objects.exists()
    assert response.context["form"].errors["address"] == [
        "An address is 500 characters or fewer."
    ]


@pytest.mark.django_db
def test_an_address_of_nothing_but_blank_lines_is_refused(client, superuser):
    client.force_login(superuser)

    response = client.post(URL, submitted(address=" \n\n  "))

    assert not Business.objects.exists()
    assert "address" in response.context["form"].errors

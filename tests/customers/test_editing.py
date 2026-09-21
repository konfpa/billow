import pytest
from django.urls import reverse

from apps.customers.models import Customer
from apps.tax.states import State
from tests.customers.conftest import KARNATAKA_GSTIN, submitted


def edit_url(customer):
    return reverse("edit_customer", args=[customer.pk])


@pytest.mark.django_db
def test_an_operator_changes_a_customers_details(client, signed_in, customer):
    response = client.post(
        edit_url(customer),
        submitted(name="Sharma Traders LLP", city="Pune", postal_code="411001"),
        follow=True,
    )

    customer.refresh_from_db()
    assert customer.city == "Pune"
    assert Customer.objects.count() == 1
    assert "Sharma Traders LLP is saved." in response.content.decode()


@pytest.mark.django_db
def test_the_form_arrives_filled_with_what_is_on_file(client, signed_in, customer):
    page = client.get(edit_url(customer)).content.decode()

    assert 'value="Sharma Traders"' in page
    assert ">\n22 Linking Road\nBandra West</textarea>" in page
    assert 'value="27AAPFU0939F1ZV"' in page


@pytest.mark.django_db
def test_a_misspelt_name_is_corrected(client, signed_in, customer):
    client.post(edit_url(customer), submitted(name="Sharma Trading"))

    customer.refresh_from_db()
    assert customer.name == "Sharma Trading"


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(client, signed_in, customer):
    response = client.post(edit_url(customer), submitted(gstin="27AAPFU0939F1ZW"))

    customer.refresh_from_db()
    assert customer.gstin == "27AAPFU0939F1ZV"
    assert customer.history.count() == 1
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_from_another_state_is_refused(client, signed_in, customer):
    response = client.post(edit_url(customer), submitted(state=State.KARNATAKA))

    customer.refresh_from_db()
    assert customer.state == State.MAHARASHTRA
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_what_editing_requires_is_what_recording_requires(client, signed_in, customer):
    form = client.get(edit_url(customer)).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Customer.REQUIRED_TO_RECORD)


@pytest.mark.django_db
def test_a_customer_without_an_address_is_refused(client, signed_in, customer):
    response = client.post(edit_url(customer), submitted(address="", city=""))

    customer.refresh_from_db()
    assert customer.address == "22 Linking Road\nBandra West"
    assert set(response.context["form"].errors) == {"address", "city"}


@pytest.mark.django_db
def test_a_customers_gstin_is_changed(client, signed_in, customer):
    client.post(
        edit_url(customer),
        submitted(
            city="Bengaluru",
            postal_code="560001",
            state=State.KARNATAKA,
            gstin=KARNATAKA_GSTIN,
        ),
    )

    customer.refresh_from_db()
    assert customer.gstin == KARNATAKA_GSTIN


@pytest.mark.django_db
def test_a_customers_gstin_is_cleared(client, signed_in, customer):
    client.post(edit_url(customer), submitted(gstin=""))

    customer.refresh_from_db()
    assert customer.gstin == ""
    assert not customer.is_registered


@pytest.mark.django_db
def test_a_gstin_typed_in_lower_case_is_stored_in_capitals(client, signed_in, customer):
    client.post(edit_url(customer), submitted(gstin="27aapfu0939f1zv"))

    customer.refresh_from_db()
    assert customer.gstin == "27AAPFU0939F1ZV"


@pytest.mark.django_db
def test_a_gstin_another_customer_holds_is_refused(client, signed_in, customer):
    other = Customer.objects.create(
        **submitted(name="Anita Desai", legal_name="", gstin=""),
    )

    page = client.post(edit_url(other), submitted(name="Anita Desai")).content.decode()

    other.refresh_from_db()
    assert other.gstin == ""
    assert "Sharma Traders already holds this GSTIN." in page


@pytest.mark.django_db
def test_keeping_its_own_gstin_is_not_a_duplicate(client, signed_in, customer):
    client.post(edit_url(customer), submitted(city="Pune", postal_code="411001"))

    customer.refresh_from_db()
    assert customer.city == "Pune"


@pytest.mark.django_db
def test_a_refused_edit_keeps_what_was_typed(client, signed_in, customer):
    page = client.post(
        edit_url(customer),
        submitted(city="Pune", gstin="27AAPFU0939F1ZW"),
    ).content.decode()

    assert 'value="Pune"' in page
    assert 'value="27AAPFU0939F1ZW"' in page
    assert "checksum" in page


@pytest.mark.django_db
def test_a_change_names_the_operator_who_made_it(client, signed_in, customer):
    client.post(edit_url(customer), submitted(city="Pune", postal_code="411001"))

    latest = customer.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_a_customer_is_reached_from_the_directory(client, signed_in, customer):
    page = client.get(reverse("customer_directory")).content.decode()

    assert f'href="{edit_url(customer)}"' in page


@pytest.mark.django_db
def test_editing_requires_signing_in(client, customer):
    url = edit_url(customer)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


@pytest.mark.django_db
def test_the_setup_gate_holds_the_form_shut(client, superuser, customer):
    client.force_login(superuser)

    response = client.post(edit_url(customer), submitted(city="Pune"))

    customer.refresh_from_db()
    assert response.status_code == 302
    assert customer.city == "Mumbai"


@pytest.mark.django_db
def test_a_customer_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.get(reverse("edit_customer", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_customers_address_is_changed_line_by_line(client, signed_in, customer):
    client.post(
        edit_url(customer),
        submitted(address="Shop 3\n22 Linking Road\nBandra West"),
    )

    page = client.get(edit_url(customer)).content.decode()
    assert ">\nShop 3\n22 Linking Road\nBandra West</textarea>" in page

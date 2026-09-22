import pytest
from django.urls import reverse

from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.suppliers.conftest import KARNATAKA_GSTIN, submitted


def edit_url(supplier):
    return reverse("edit_supplier", args=[supplier.pk])


@pytest.mark.django_db
def test_an_operator_changes_a_suppliers_details(client, signed_in, supplier):
    response = client.post(
        edit_url(supplier),
        submitted(
            name="Mehta Pipes Private Limited", city="Nashik", postal_code="422001"
        ),
        follow=True,
    )

    supplier.refresh_from_db()
    assert supplier.city == "Nashik"
    assert Supplier.objects.count() == 1
    assert "Mehta Pipes Private Limited is saved." in response.content.decode()


@pytest.mark.django_db
def test_the_form_arrives_filled_with_what_is_on_file(client, signed_in, supplier):
    page = client.get(edit_url(supplier)).content.decode()

    assert 'value="Mehta Pipes"' in page
    assert ">\nPlot 14, MIDC\nBhosari</textarea>" in page
    assert 'value="27AAACM1234K1ZN"' in page


@pytest.mark.django_db
def test_a_misspelt_name_is_corrected(client, signed_in, supplier):
    client.post(edit_url(supplier), submitted(name="Mehta Pipe Works"))

    supplier.refresh_from_db()
    assert supplier.name == "Mehta Pipe Works"


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(client, signed_in, supplier):
    response = client.post(edit_url(supplier), submitted(gstin="27AAACM1234K1ZM"))

    supplier.refresh_from_db()
    assert supplier.gstin == "27AAACM1234K1ZN"
    assert supplier.history.count() == 1
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_from_another_state_is_refused(client, signed_in, supplier):
    response = client.post(edit_url(supplier), submitted(state=State.KARNATAKA))

    supplier.refresh_from_db()
    assert supplier.state == State.MAHARASHTRA
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_what_editing_requires_is_what_recording_requires(client, signed_in, supplier):
    form = client.get(edit_url(supplier)).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Supplier.REQUIRED_TO_RECORD)


@pytest.mark.django_db
def test_a_supplier_without_an_address_is_refused(client, signed_in, supplier):
    response = client.post(edit_url(supplier), submitted(address="", city=""))

    supplier.refresh_from_db()
    assert supplier.address == "Plot 14, MIDC\nBhosari"
    assert set(response.context["form"].errors) == {"address", "city"}


@pytest.mark.django_db
def test_a_suppliers_gstin_is_changed(client, signed_in, supplier):
    client.post(
        edit_url(supplier),
        submitted(
            city="Bengaluru",
            postal_code="560001",
            state=State.KARNATAKA,
            gstin=KARNATAKA_GSTIN,
        ),
    )

    supplier.refresh_from_db()
    assert supplier.gstin == KARNATAKA_GSTIN


@pytest.mark.django_db
def test_a_suppliers_gstin_is_cleared(client, signed_in, supplier):
    client.post(edit_url(supplier), submitted(gstin=""))

    supplier.refresh_from_db()
    assert supplier.gstin == ""
    assert not supplier.is_registered


@pytest.mark.django_db
def test_a_gstin_typed_in_lower_case_is_stored_in_capitals(client, signed_in, supplier):
    client.post(edit_url(supplier), submitted(gstin="27aaacm1234k1zn"))

    supplier.refresh_from_db()
    assert supplier.gstin == "27AAACM1234K1ZN"


@pytest.mark.django_db
def test_a_gstin_another_supplier_holds_is_refused(client, signed_in, supplier):
    other = Supplier.objects.create(
        **submitted(name="Anita Desai", legal_name="", gstin=""),
    )

    page = client.post(edit_url(other), submitted(name="Anita Desai")).content.decode()

    other.refresh_from_db()
    assert other.gstin == ""
    assert "Mehta Pipes already holds this GSTIN." in page


@pytest.mark.django_db
def test_keeping_its_own_gstin_is_not_a_duplicate(client, signed_in, supplier):
    client.post(edit_url(supplier), submitted(city="Nashik", postal_code="422001"))

    supplier.refresh_from_db()
    assert supplier.city == "Nashik"


@pytest.mark.django_db
def test_a_refused_edit_keeps_what_was_typed(client, signed_in, supplier):
    page = client.post(
        edit_url(supplier),
        submitted(city="Nashik", gstin="27AAACM1234K1ZM"),
    ).content.decode()

    assert 'value="Nashik"' in page
    assert 'value="27AAACM1234K1ZM"' in page
    assert "checksum" in page


@pytest.mark.django_db
def test_a_change_names_the_operator_who_made_it(client, signed_in, supplier):
    client.post(edit_url(supplier), submitted(city="Nashik", postal_code="422001"))

    latest = supplier.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in


@pytest.mark.django_db
def test_a_saved_edit_returns_to_the_supplier(client, signed_in, supplier):
    response = client.post(edit_url(supplier), submitted(city="Nashik"))

    assert response.url == reverse("supplier_detail", args=[supplier.pk])


@pytest.mark.django_db
def test_the_back_link_returns_to_the_supplier(client, signed_in, supplier):
    page = client.get(edit_url(supplier)).content.decode()

    assert f'href="{reverse("supplier_detail", args=[supplier.pk])}"' in page


@pytest.mark.django_db
def test_archiving_is_not_offered_while_editing(client, signed_in, supplier):
    page = client.get(edit_url(supplier)).content.decode()

    assert reverse("archive_supplier", args=[supplier.pk]) not in page
    assert reverse("restore_supplier", args=[supplier.pk]) not in page


@pytest.mark.django_db
def test_editing_requires_signing_in(client, supplier):
    url = edit_url(supplier)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


@pytest.mark.django_db
def test_the_setup_gate_holds_the_form_shut(client, superuser, supplier):
    client.force_login(superuser)

    response = client.post(edit_url(supplier), submitted(city="Nashik"))

    supplier.refresh_from_db()
    assert response.status_code == 302
    assert supplier.city == "Pune"


@pytest.mark.django_db
def test_a_supplier_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.get(reverse("edit_supplier", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_suppliers_address_is_changed_line_by_line(client, signed_in, supplier):
    client.post(
        edit_url(supplier),
        submitted(address="Shop 3\nPlot 14, MIDC\nBhosari"),
    )

    page = client.get(edit_url(supplier)).content.decode()
    assert ">\nShop 3\nPlot 14, MIDC\nBhosari</textarea>" in page

import pytest
from django.urls import reverse

from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.suppliers.conftest import KARNATAKA_GSTIN, submitted

DIRECTORY = reverse("supplier_directory")
RECORD = reverse("record_supplier")


@pytest.mark.django_db
def test_the_directory_requires_signing_in(client):
    response = client.get(DIRECTORY)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={DIRECTORY}"


@pytest.mark.django_db
def test_the_directory_lists_the_suppliers_on_file(client, signed_in, supplier):
    page = client.get(DIRECTORY).content.decode()

    assert "Mehta Pipes" in page
    assert "27AAACM1234K1ZN" in page


@pytest.mark.django_db
def test_an_empty_directory_says_so(client, signed_in):
    response = client.get(DIRECTORY)

    assert response.status_code == 200
    assert len(response.context["suppliers"]) == 0


@pytest.mark.django_db
def test_an_operator_records_a_registered_supplier(client, signed_in):
    response = client.post(RECORD, submitted(), follow=True)

    assert response.status_code == 200
    supplier = Supplier.objects.get()
    assert supplier.gstin == "27AAACM1234K1ZN"
    assert "Mehta Pipes" in response.content.decode()


@pytest.mark.django_db
def test_an_operator_records_an_unregistered_supplier(client, signed_in):
    response = client.post(
        RECORD,
        submitted(name="Anita Desai", legal_name="", gstin=""),
        follow=True,
    )

    supplier = Supplier.objects.get()
    assert supplier.gstin == ""
    assert not supplier.is_registered
    assert "Anita Desai" in response.content.decode()


@pytest.mark.django_db
def test_what_recording_requires_is_what_the_form_demands(client, signed_in):
    form = client.get(RECORD).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Supplier.REQUIRED_TO_RECORD)


@pytest.mark.django_db
def test_the_state_is_chosen_from_a_list(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert '<select name="state"' in page
    assert '<option value="27">Maharashtra</option>' in page


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(gstin="27AAACM1234K1ZM"))

    assert response.status_code == 200
    assert not Supplier.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_from_another_state_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(state=State.KARNATAKA))

    assert not Supplier.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_typed_in_lower_case_is_stored_in_capitals(client, signed_in):
    client.post(RECORD, submitted(gstin="27aaacm1234k1zn"))

    assert Supplier.objects.get().gstin == "27AAACM1234K1ZN"


@pytest.mark.django_db
def test_a_supplier_without_an_address_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(address="", city=""))

    assert not Supplier.objects.exists()
    assert set(response.context["form"].errors) == {"address", "city"}


@pytest.mark.django_db
def test_a_refused_submission_keeps_what_was_already_typed(client, signed_in):
    page = client.post(RECORD, submitted(gstin="27AAACM1234K1ZM")).content.decode()

    assert "Mehta Pipes" in page
    assert "Plot 14, MIDC" in page
    assert "27AAACM1234K1ZM" in page
    assert "checksum" in page


@pytest.mark.django_db
def test_a_blank_legal_name_is_not_a_copy_of_the_display_name(client, signed_in):
    client.post(RECORD, submitted(legal_name=""))

    supplier = Supplier.objects.get()
    assert supplier.legal_name == ""
    assert supplier.invoice_name == "Mehta Pipes"


@pytest.mark.django_db
def test_recording_a_supplier_names_the_operator_who_did_it(client, signed_in):
    client.post(RECORD, submitted())

    assert Supplier.objects.get().history.latest().history_user == signed_in


@pytest.mark.django_db
def test_the_form_requires_signing_in(client):
    response = client.get(RECORD)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={RECORD}"


@pytest.mark.django_db
def test_the_setup_gate_holds_the_directory_shut(client, superuser):
    """The gate covers a page by its having been written, not by opting in."""
    client.force_login(superuser)

    response = client.get(DIRECTORY)

    assert response.status_code == 302
    assert response.url == reverse("business_settings")


@pytest.mark.django_db
def test_the_setup_gate_holds_the_form_shut(client, superuser):
    client.force_login(superuser)

    response = client.post(RECORD, submitted())

    assert response.status_code == 302
    assert not Supplier.objects.exists()


@pytest.mark.django_db
def test_the_directory_is_reachable_from_every_page(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert f'href="{DIRECTORY}"' in home


@pytest.mark.django_db
def test_an_operator_who_cannot_set_billow_up_is_told_so_instead(client, buyer):
    client.force_login(buyer)

    response = client.get(DIRECTORY)

    assert response.status_code == 200
    assert "needs setting up" in response.content.decode()


@pytest.mark.django_db
def test_the_state_is_chosen_from_a_list_that_starts_unanswered(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert "Choose a state" in page


@pytest.mark.django_db
def test_saving_a_supplier_is_confirmed(client, signed_in):
    page = client.post(RECORD, submitted(), follow=True).content.decode()

    assert "Mehta Pipes is saved." in page


@pytest.mark.django_db
def test_a_gstin_already_on_file_is_refused_naming_who_holds_it(
    client,
    signed_in,
    supplier,
):
    page = client.post(RECORD, submitted(name="Mehta Pipe Works")).content.decode()

    assert Supplier.objects.count() == 1
    assert "Mehta Pipes already holds this GSTIN." in page


@pytest.mark.django_db
def test_the_same_gstin_in_lower_case_is_refused_as_a_duplicate(
    client,
    signed_in,
    supplier,
):
    page = client.post(RECORD, submitted(gstin="27aaacm1234k1zn")).content.decode()

    assert Supplier.objects.count() == 1
    assert "Mehta Pipes already holds this GSTIN." in page


@pytest.mark.django_db
def test_two_suppliers_may_share_a_display_name(client, signed_in, supplier):
    page = client.post(RECORD, submitted(gstin=""), follow=True).content.decode()

    assert Supplier.objects.filter(name="Mehta Pipes").count() == 2
    assert "already holds" not in page


@pytest.mark.django_db
def test_any_number_of_suppliers_may_hold_no_gstin(client, signed_in):
    for name in ("Anita Desai", "Ravi Kumar", "Meera Iyer"):
        client.post(RECORD, submitted(name=name, legal_name="", gstin=""))

    assert Supplier.objects.count() == 3


@pytest.mark.django_db
def test_one_company_registered_in_two_states_is_two_suppliers(
    client,
    signed_in,
    supplier,
):
    page = client.post(
        RECORD,
        submitted(
            city="Bengaluru",
            postal_code="560001",
            state=State.KARNATAKA,
            gstin=KARNATAKA_GSTIN,
        ),
        follow=True,
    ).content.decode()

    assert Supplier.objects.count() == 2
    assert KARNATAKA_GSTIN in page


@pytest.mark.django_db
def test_an_empty_directory_says_nobody_is_on_file(client, signed_in):
    page = client.get(DIRECTORY).content.decode()

    assert "Nobody on file yet" in page
    assert "Nobody archived" not in page


@pytest.mark.django_db
def test_an_empty_archive_says_nobody_is_archived(client, signed_in, supplier):
    page = client.get(DIRECTORY, {"show": "archived"}).content.decode()

    assert "Nobody archived" in page
    assert "Nobody on file yet" not in page


@pytest.mark.django_db
def test_a_search_of_the_archived_matching_nothing_points_to_those_on_file(
    client,
    signed_in,
):
    page = client.get(DIRECTORY, {"show": "archived", "q": "Kapoor"}).content.decode()

    assert "No Supplier matches “Kapoor”" in page
    assert "in case they return" not in page
    assert f'href="{DIRECTORY}?q=Kapoor"' in page


@pytest.mark.django_db
def test_a_suppliers_address_keeps_the_lines_it_was_typed_on(client, signed_in):
    client.post(RECORD, submitted(address=" Shop 3, Linking Road \n\nBandra West\n"))

    assert Supplier.objects.get().address == "Shop 3, Linking Road\nBandra West"


@pytest.mark.django_db
def test_a_suppliers_address_of_six_lines_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(address="1\n2\n3\n4\n5\n6"))

    assert not Supplier.objects.exists()
    assert response.context["form"].errors["address"] == [
        "An address fits on 5 lines or fewer."
    ]


@pytest.mark.django_db
def test_a_suppliers_address_longer_than_500_characters_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(address="x" * 501))

    assert not Supplier.objects.exists()
    assert response.context["form"].errors["address"] == [
        "An address is 500 characters or fewer."
    ]


@pytest.mark.django_db
def test_every_row_leads_to_the_supplier(client, signed_in, supplier):
    page = client.get(DIRECTORY).content.decode()

    detail = reverse("supplier_detail", args=[supplier.pk])
    assert page.count(f'href="{detail}"') == 2
    assert f'href="{reverse("edit_supplier", args=[supplier.pk])}"' not in page


@pytest.mark.django_db
def test_a_firm_on_file_as_a_customer_is_recorded_as_a_supplier(client, signed_in):
    Customer.objects.create(**submitted(name="Mehta Pipes (sales)"))

    page = client.post(RECORD, submitted(), follow=True).content.decode()

    assert Supplier.objects.get().gstin == "27AAACM1234K1ZN"
    assert "already holds" not in page


@pytest.mark.django_db
def test_the_state_is_explained_as_deciding_input_tax(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert "CGST plus SGST or IGST" in page
    assert "place of supply" not in page

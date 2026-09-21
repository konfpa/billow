import pytest
from django.urls import reverse

from apps.customers.models import Customer
from apps.tax.states import State
from tests.customers.conftest import KARNATAKA_GSTIN, submitted

DIRECTORY = reverse("customer_directory")
RECORD = reverse("record_customer")


@pytest.mark.django_db
def test_the_directory_requires_signing_in(client):
    response = client.get(DIRECTORY)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={DIRECTORY}"


@pytest.mark.django_db
def test_the_directory_lists_the_customers_on_file(client, signed_in, customer):
    page = client.get(DIRECTORY).content.decode()

    assert "Sharma Traders" in page
    assert "27AAPFU0939F1ZV" in page


@pytest.mark.django_db
def test_an_empty_directory_says_so(client, signed_in):
    response = client.get(DIRECTORY)

    assert response.status_code == 200
    assert response.context["customers"].count() == 0


@pytest.mark.django_db
def test_an_operator_records_a_registered_customer(client, signed_in):
    response = client.post(RECORD, submitted(), follow=True)

    assert response.status_code == 200
    customer = Customer.objects.get()
    assert customer.gstin == "27AAPFU0939F1ZV"
    assert "Sharma Traders" in response.content.decode()


@pytest.mark.django_db
def test_an_operator_records_an_unregistered_customer(client, signed_in):
    response = client.post(
        RECORD,
        submitted(name="Anita Desai", legal_name="", gstin=""),
        follow=True,
    )

    customer = Customer.objects.get()
    assert customer.gstin == ""
    assert not customer.is_registered
    assert "Anita Desai" in response.content.decode()


@pytest.mark.django_db
def test_what_recording_requires_is_what_the_form_demands(client, signed_in):
    form = client.get(RECORD).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Customer.REQUIRED_TO_RECORD)


@pytest.mark.django_db
def test_the_state_is_chosen_from_a_list(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert '<select name="state"' in page
    assert '<option value="27">Maharashtra</option>' in page


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(gstin="27AAPFU0939F1ZW"))

    assert response.status_code == 200
    assert not Customer.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_from_another_state_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(state=State.KARNATAKA))

    assert not Customer.objects.exists()
    assert "gstin" in response.context["form"].errors


@pytest.mark.django_db
def test_a_gstin_typed_in_lower_case_is_stored_in_capitals(client, signed_in):
    client.post(RECORD, submitted(gstin="27aapfu0939f1zv"))

    assert Customer.objects.get().gstin == "27AAPFU0939F1ZV"


@pytest.mark.django_db
def test_a_customer_without_an_address_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(address_line_1="", city=""))

    assert not Customer.objects.exists()
    assert set(response.context["form"].errors) == {"address_line_1", "city"}


@pytest.mark.django_db
def test_a_refused_submission_keeps_what_was_already_typed(client, signed_in):
    page = client.post(RECORD, submitted(gstin="27AAPFU0939F1ZW")).content.decode()

    assert "Sharma Traders" in page
    assert "22 Linking Road" in page
    assert "27AAPFU0939F1ZW" in page
    assert "checksum" in page


@pytest.mark.django_db
def test_a_blank_legal_name_is_not_a_copy_of_the_display_name(client, signed_in):
    client.post(RECORD, submitted(legal_name=""))

    customer = Customer.objects.get()
    assert customer.legal_name == ""
    assert customer.invoice_name == "Sharma Traders"


@pytest.mark.django_db
def test_recording_a_customer_names_the_operator_who_did_it(client, signed_in):
    client.post(RECORD, submitted())

    assert Customer.objects.get().history.latest().history_user == signed_in


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
    assert not Customer.objects.exists()


@pytest.mark.django_db
def test_the_directory_is_reachable_from_every_page(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert f'href="{DIRECTORY}"' in home


@pytest.mark.django_db
def test_an_operator_who_cannot_set_billow_up_is_told_so_instead(client, operator):
    client.force_login(operator)

    response = client.get(DIRECTORY)

    assert response.status_code == 200
    assert "needs setting up" in response.content.decode()


@pytest.mark.django_db
def test_the_state_is_chosen_from_a_list_that_starts_unanswered(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert "Choose a state" in page


@pytest.mark.django_db
def test_saving_a_customer_is_confirmed(client, signed_in):
    page = client.post(RECORD, submitted(), follow=True).content.decode()

    assert "Sharma Traders is saved." in page


@pytest.mark.django_db
def test_a_gstin_already_on_file_is_refused_naming_who_holds_it(
    client,
    signed_in,
    customer,
):
    page = client.post(RECORD, submitted(name="Sharma Trading")).content.decode()

    assert Customer.objects.count() == 1
    assert "Sharma Traders already holds this GSTIN." in page


@pytest.mark.django_db
def test_the_same_gstin_in_lower_case_is_refused_as_a_duplicate(
    client,
    signed_in,
    customer,
):
    page = client.post(RECORD, submitted(gstin="27aapfu0939f1zv")).content.decode()

    assert Customer.objects.count() == 1
    assert "Sharma Traders already holds this GSTIN." in page


@pytest.mark.django_db
def test_two_customers_may_share_a_display_name(client, signed_in, customer):
    page = client.post(RECORD, submitted(gstin=""), follow=True).content.decode()

    assert Customer.objects.filter(name="Sharma Traders").count() == 2
    assert "already holds" not in page


@pytest.mark.django_db
def test_any_number_of_customers_may_hold_no_gstin(client, signed_in):
    for name in ("Anita Desai", "Ravi Kumar", "Meera Iyer"):
        client.post(RECORD, submitted(name=name, legal_name="", gstin=""))

    assert Customer.objects.count() == 3


@pytest.mark.django_db
def test_one_company_registered_in_two_states_is_two_customers(
    client,
    signed_in,
    customer,
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

    assert Customer.objects.count() == 2
    assert KARNATAKA_GSTIN in page


@pytest.mark.django_db
def test_an_empty_directory_says_nobody_is_on_file(client, signed_in):
    page = client.get(DIRECTORY).content.decode()

    assert "Nobody on file yet" in page
    assert "Nobody archived" not in page


@pytest.mark.django_db
def test_an_empty_archive_says_nobody_is_archived(client, signed_in, customer):
    page = client.get(DIRECTORY, {"show": "archived"}).content.decode()

    assert "Nobody archived" in page
    assert "Nobody on file yet" not in page


@pytest.mark.django_db
def test_a_search_of_the_archived_matching_nothing_points_to_those_on_file(
    client,
    signed_in,
):
    page = client.get(DIRECTORY, {"show": "archived", "q": "Kapoor"}).content.decode()

    assert "No Customer matches “Kapoor”" in page
    assert "in case they return" not in page
    assert f'href="{DIRECTORY}?q=Kapoor"' in page

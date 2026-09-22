import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.suppliers.conftest import REGISTERED


@pytest.mark.django_db
def test_a_supplier_trading_under_its_registered_name_stores_one_name(supplier):
    supplier.legal_name = ""
    supplier.save()

    assert supplier.legal_name == ""
    assert supplier.invoice_name == supplier.name


@pytest.mark.django_db
def test_a_legal_name_is_what_a_tax_invoice_carries(supplier):
    assert supplier.invoice_name == "Mehta Pipes Private Limited"


@pytest.mark.django_db
def test_a_supplier_holding_a_gstin_is_registered(supplier):
    assert supplier.is_registered


@pytest.mark.django_db
def test_a_supplier_holding_no_gstin_is_unregistered(supplier):
    supplier.gstin = ""

    assert not supplier.is_registered


@pytest.mark.django_db
def test_the_absence_of_a_gstin_is_the_whole_distinction(db):
    unregistered = Supplier.objects.create(
        name="Anita Desai",
        address="4 Ashok Marg",
        city="Jaipur",
        postal_code="302001",
        state="08",
    )

    assert not unregistered.is_registered


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(supplier):
    supplier.gstin = "27AAACM1234K1ZM"

    with pytest.raises(ValidationError) as refusal:
        supplier.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_a_gstin_must_embed_the_state_that_was_chosen(supplier):
    supplier.state = State.KARNATAKA

    with pytest.raises(ValidationError) as refusal:
        supplier.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_an_unregistered_supplier_is_complete_without_a_gstin(supplier):
    supplier.gstin = ""

    supplier.full_clean()


@pytest.mark.django_db
def test_changing_a_supplier_is_recorded(supplier):
    supplier.city = "Nashik"
    supplier.save()

    assert [record.history_type for record in supplier.history.all()] == ["~", "+"]


@pytest.mark.django_db
def test_a_change_names_the_operator_who_made_it(supplier, buyer):
    supplier._history_user = buyer  # noqa: SLF001 — simple_history's documented hook
    supplier.city = "Nashik"
    supplier.save()

    assert supplier.history.latest().history_user == buyer


@pytest.mark.django_db
def test_a_second_supplier_on_one_registration_is_refused(supplier):
    twin = Supplier(**{**REGISTERED, "name": "Mehta Pipe Works"})

    with pytest.raises(ValidationError) as refusal:
        twin.full_clean()

    assert "Mehta Pipes already holds" in str(refusal.value.error_dict["gstin"])


@pytest.mark.django_db
def test_a_supplier_is_not_a_duplicate_of_itself(supplier):
    supplier.city = "Nashik"

    supplier.full_clean()


@pytest.mark.django_db
def test_raw_sql_cannot_write_a_second_supplier_on_one_registration(supplier):
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as c:
        c.execute(
            "INSERT INTO suppliers_supplier (name, legal_name, address, city,"
            " postal_code, state, gstin, email, phone, created_at, updated_at)"
            " SELECT name, legal_name, address, city, postal_code, state, gstin,"
            " email, phone, created_at, updated_at FROM suppliers_supplier",
        )


@pytest.mark.django_db
def test_a_supplier_archived_on_one_registration_still_holds_it(archived):
    twin = Supplier(**{**REGISTERED, "name": "Mehta Pipe Works"})

    with pytest.raises(ValidationError) as refusal:
        twin.full_clean()

    assert "They are archived, and can be restored." in str(
        refusal.value.error_dict["gstin"]
    )


@pytest.mark.django_db
def test_a_customer_on_the_same_registration_is_no_duplicate(db):
    Customer.objects.create(**{**REGISTERED, "name": "Mehta Pipes (sales)"})

    Supplier(**REGISTERED).full_clean()


@pytest.mark.django_db
def test_a_supplier_on_the_same_registration_is_no_duplicate_customer(supplier):
    Customer(**{**REGISTERED, "name": "Mehta Pipes (sales)"}).full_clean()

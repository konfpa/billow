import pytest
from django.core.exceptions import ValidationError

from apps.customers.models import Customer
from apps.tax.states import State


@pytest.mark.django_db
def test_a_customer_trading_under_its_registered_name_stores_one_name(customer):
    customer.legal_name = ""
    customer.save()

    assert customer.legal_name == ""
    assert customer.invoice_name == customer.name


@pytest.mark.django_db
def test_a_legal_name_is_what_a_tax_invoice_carries(customer):
    assert customer.invoice_name == "Sharma Traders LLP"


@pytest.mark.django_db
def test_a_customer_holding_a_gstin_is_registered(customer):
    assert customer.is_registered


@pytest.mark.django_db
def test_a_customer_holding_no_gstin_is_unregistered(customer):
    customer.gstin = ""

    assert not customer.is_registered


@pytest.mark.django_db
def test_the_absence_of_a_gstin_is_the_whole_distinction(db):
    unregistered = Customer.objects.create(
        name="Anita Desai",
        address_line_1="4 Ashok Marg",
        city="Jaipur",
        postal_code="302001",
        state="08",
    )

    assert not unregistered.is_registered


@pytest.mark.django_db
def test_a_gstin_failing_its_checksum_is_refused(customer):
    customer.gstin = "27AAPFU0939F1ZW"

    with pytest.raises(ValidationError) as refusal:
        customer.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_a_gstin_must_embed_the_state_that_was_chosen(customer):
    customer.state = State.KARNATAKA

    with pytest.raises(ValidationError) as refusal:
        customer.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_an_unregistered_customer_is_complete_without_a_gstin(customer):
    customer.gstin = ""

    customer.full_clean()


@pytest.mark.django_db
def test_changing_a_customer_is_recorded(customer):
    customer.city = "Pune"
    customer.save()

    assert [record.history_type for record in customer.history.all()] == ["~", "+"]


@pytest.mark.django_db
def test_a_change_names_the_operator_who_made_it(customer, operator):
    customer._history_user = operator  # noqa: SLF001 — simple_history's documented hook
    customer.city = "Pune"
    customer.save()

    assert customer.history.latest().history_user == operator

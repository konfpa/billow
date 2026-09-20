import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.business.models import Business
from apps.tax.states import State


@pytest.mark.django_db
def test_a_business_trading_under_its_registered_name_stores_one_name(business):
    business.legal_name = ""
    business.save()

    assert business.legal_name == ""
    assert business.invoice_name == business.name


@pytest.mark.django_db
def test_a_legal_name_is_what_a_tax_invoice_carries(business):
    business.legal_name = "Umbrella Trading Private Limited"
    business.save()

    assert business.invoice_name == "Umbrella Trading Private Limited"


@pytest.mark.django_db
def test_raw_sql_cannot_write_a_second_business(business):
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as c:
        c.execute(
            "INSERT INTO business_business (id, name, legal_name, address_line_1,"
            " address_line_2, city, postal_code, state, is_gst_registered, gstin,"
            " pan, cin, email, phone, website, logo, created_at, updated_at)"
            " SELECT 2, name, legal_name, address_line_1, address_line_2, city,"
            " postal_code, state, is_gst_registered, gstin, pan, cin, email,"
            " phone, website, logo, created_at, updated_at FROM business_business",
        )


@pytest.mark.django_db
def test_the_business_is_loaded_rather_than_looked_up(business):
    assert Business.load().pk == business.pk


@pytest.mark.django_db
def test_loading_before_setup_yields_an_unsaved_business(db):
    assert Business.load().pk is None


@pytest.mark.django_db
def test_a_gstin_is_required_of_a_registered_business(business):
    business.is_gst_registered = True
    business.gstin = ""

    with pytest.raises(ValidationError) as refusal:
        business.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_an_unregistered_business_may_not_hold_a_gstin(business):
    business.is_gst_registered = False
    business.gstin = "27AAPFU0939F1ZV"

    with pytest.raises(ValidationError) as refusal:
        business.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_an_unregistered_business_is_complete_without_a_gstin(business):
    business.is_gst_registered = False
    business.gstin = ""

    business.full_clean()


@pytest.mark.django_db
def test_a_gstin_must_embed_the_state_that_was_chosen(business):
    business.state = State.KARNATAKA
    business.gstin = "27AAPFU0939F1ZV"

    with pytest.raises(ValidationError) as refusal:
        business.full_clean()

    assert "gstin" in refusal.value.error_dict


@pytest.mark.django_db
def test_an_unanswered_gst_registration_is_missing_for_setup(business):
    business.is_gst_registered = None

    assert "is_gst_registered" in business.missing_for_setup()


@pytest.mark.django_db
def test_answering_no_to_gst_registration_is_an_answer(business):
    business.is_gst_registered = False

    assert "is_gst_registered" not in business.missing_for_setup()


@pytest.mark.django_db
def test_a_business_missing_nothing_required_is_ready(business):
    assert business.missing_for_setup() == ()


@pytest.mark.django_db
def test_what_setup_requires_is_declared_once(business):
    for field in Business.REQUIRED_FOR_SETUP:
        setattr(business, field, None)

    assert set(business.missing_for_setup()) == set(Business.REQUIRED_FOR_SETUP)


@pytest.mark.django_db
def test_changing_the_business_is_recorded(business):
    business.name = "Umbrella Supplies"
    business.save()

    assert [record.history_type for record in business.history.all()] == ["~", "+"]

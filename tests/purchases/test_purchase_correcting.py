from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import ItemUnit
from apps.purchases.models import Purchase
from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.purchases.conftest import as_it_stands, line, submitted

RECORD = reverse("record_purchase")


def edit_url(purchase):
    return reverse("edit_purchase", args=[purchase.pk])


def detail_url(purchase):
    return reverse("purchase_detail", args=[purchase.pk])


@pytest.fixture
def signed_in(client, business, corrector):
    client.force_login(corrector)
    return corrector


@pytest.fixture
def purchase(client, signed_in, supplier, elbow):
    """Ten elbows at ₹100, recorded through the form."""
    client.post(RECORD, submitted(supplier, line(elbow)))
    return Purchase.objects.get()


@pytest.mark.django_db
def test_the_form_arrives_filled_with_what_is_on_file(client, purchase):
    page = client.get(edit_url(purchase)).content.decode()

    assert 'value="MP/2026-27/0412"' in page
    assert 'value="CPVC elbow ¾ inch"' in page
    assert 'value="10.000"' in page
    assert 'value="1180.00"' in page


@pytest.mark.django_db
def test_a_mistyped_bill_number_is_corrected(client, purchase):
    response = client.post(
        edit_url(purchase), as_it_stands(purchase, bill_number="MP/2026-27/0421")
    )

    purchase.refresh_from_db()
    assert response.status_code == 302
    assert response.url == detail_url(purchase)
    assert purchase.bill_number == "MP/2026-27/0421"
    assert Purchase.objects.count() == 1


@pytest.mark.django_db
def test_saving_a_bill_unchanged_is_not_refused_as_its_own_duplicate(client, purchase):
    response = client.post(edit_url(purchase), as_it_stands(purchase), follow=True)

    assert "Bill MP/2026-27/0412 from Mehta Pipes is saved." in (
        response.content.decode()
    )


@pytest.mark.django_db
def test_a_line_is_corrected(client, purchase, elbow):
    client.post(
        edit_url(purchase),
        as_it_stands(
            purchase,
            **{"lines-0-quantity": "12", "lines-0-rate": "95.00"},
            billed_total="1345.20",
        ),
    )

    corrected = purchase.lines.get()
    assert (corrected.item, corrected.quantity, corrected.rate) == (
        elbow,
        Decimal("12.000"),
        Decimal("95.00"),
    )


@pytest.mark.django_db
def test_a_line_is_removed_and_another_added(client, purchase, pipe):
    posted = as_it_stands(
        purchase,
        **{
            "lines-0-DELETE": "on",
            "lines-TOTAL_FORMS": "2",
            "lines-1-item": str(pipe.pk),
            "lines-1-unit": "NOS",
            "lines-1-quantity": "4",
            "lines-1-rate": "250.00",
        },
        billed_total="1050.00",
    )

    client.post(edit_url(purchase), posted)

    assert [(line.item, line.quantity) for line in purchase.lines.all()] == [
        (pipe, Decimal("4.000"))
    ]


@pytest.mark.django_db
def test_a_correction_that_repeats_another_bill_is_refused(
    client, purchase, supplier, elbow
):
    client.post(RECORD, submitted(supplier, line(elbow), bill_number="MP/0413"))

    response = client.post(
        edit_url(purchase), as_it_stands(purchase, bill_number="MP/0413")
    )

    purchase.refresh_from_db()
    assert purchase.bill_number == "MP/2026-27/0412"
    assert "bill_number" in response.context["form"].errors


@pytest.mark.django_db
def test_a_bill_from_a_supplier_archived_since_opens_and_saves(
    client, purchase, supplier
):
    supplier.archive()

    page = client.get(edit_url(purchase))
    response = client.post(
        edit_url(purchase), as_it_stands(purchase, bill_number="MP/0412")
    )

    purchase.refresh_from_db()
    assert page.status_code == 200
    assert response.status_code == 302
    assert purchase.supplier == supplier
    assert purchase.bill_number == "MP/0412"


@pytest.mark.django_db
def test_the_supplier_picker_offers_the_archived_supplier_named_and_no_other(
    client, purchase, supplier, karnataka_supplier
):
    supplier.archive()
    karnataka_supplier.archive()

    choices = client.get(edit_url(purchase)).context["form"].fields["supplier"]

    assert list(choices.queryset) == [supplier]


@pytest.mark.django_db
def test_a_line_naming_an_item_archived_since_opens_and_saves(client, purchase, elbow):
    elbow.archive()

    page = client.get(edit_url(purchase)).content.decode()
    response = client.post(
        edit_url(purchase),
        as_it_stands(purchase, **{"lines-0-rate": "90.00"}, billed_total="1062.00"),
    )

    corrected = purchase.lines.get()
    assert 'value="CPVC elbow ¾ inch"' in page
    assert response.status_code == 302
    assert (corrected.item, corrected.rate) == (elbow, Decimal("90.00"))


@pytest.mark.django_db
def test_an_archived_item_cannot_be_put_on_a_line_it_was_not_on(client, purchase, pipe):
    pipe.archive()

    response = client.post(
        edit_url(purchase), as_it_stands(purchase, **{"lines-0-item": str(pipe.pk)})
    )

    assert response.status_code == 200
    assert purchase.lines.get().item != pipe


@pytest.mark.django_db
def test_a_correction_keeps_the_suppliers_registration_as_recorded(
    client, purchase, supplier
):
    Supplier.objects.filter(pk=supplier.pk).update(
        state=State.KARNATAKA, gstin="29AAACM1234K1ZJ"
    )

    client.post(edit_url(purchase), as_it_stands(purchase, bill_number="MP/0412"))

    purchase.refresh_from_db()
    assert purchase.supplier_state == State.MAHARASHTRA
    assert purchase.supplier_gstin == "27AAACM1234K1ZN"


@pytest.mark.django_db
def test_a_bill_moved_to_another_supplier_takes_their_registration(
    client, purchase, karnataka_supplier
):
    client.post(
        edit_url(purchase),
        as_it_stands(purchase, supplier=str(karnataka_supplier.pk)),
    )

    purchase.refresh_from_db()
    assert purchase.supplier == karnataka_supplier
    assert purchase.supplier_state == State.KARNATAKA
    assert purchase.supplier_gstin == "29AAACM1234K1ZJ"


@pytest.mark.django_db
def test_a_correction_keeps_the_units_a_line_was_billed_in(
    client, signed_in, supplier, pipe
):
    client.post(
        RECORD,
        submitted(
            supplier,
            line(pipe, unit="BDL", quantity="2", rate="400.00"),
            billed_total="840.00",
        ),
    )
    purchase = Purchase.objects.get()
    ItemUnit.objects.filter(item=pipe, code="BDL").update(rate=25)

    client.post(edit_url(purchase), as_it_stands(purchase, bill_number="MP/0412"))

    assert purchase.lines.get().stock_units_in_one == Decimal(20)


@pytest.mark.django_db
def test_the_grand_total_check_applies_to_a_correction(client, purchase):
    response = client.post(
        edit_url(purchase), as_it_stands(purchase, **{"lines-0-quantity": "11"})
    )

    purchase.refresh_from_db()
    assert response.context["form"].total_check is not None
    assert purchase.lines.get().quantity == Decimal(10)


@pytest.mark.django_db
def test_a_correction_is_kept_in_history_naming_who_made_it(
    client, purchase, signed_in
):
    client.post(
        edit_url(purchase),
        as_it_stands(purchase, **{"lines-0-rate": "90.00"}, billed_total="1062.00"),
    )

    changed = purchase.history.latest()
    changed_line = purchase.lines.get().history.latest()
    assert (changed.history_type, changed.history_user) == ("~", signed_in)
    assert (changed_line.history_type, changed_line.history_user) == ("~", signed_in)
    assert changed_line.prev_record.rate == Decimal("100.00")

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import Item
from tests.catalogue.conftest import record, submitted

RECORD = reverse("record_item")
DIRECTORY = reverse("item_directory")


@pytest.mark.django_db
def test_an_operator_records_a_goods_item(client, signed_in):
    response = client.post(RECORD, submitted(), follow=True)

    item = Item.objects.get()
    assert item.name == "Jaquar Florentine tap, chrome"
    assert item.kind == Item.Kind.GOODS
    assert item.hsn_sac == "848180"
    assert item.gst_rate == Decimal("18.00")
    assert item.stock_unit.uqc == "NOS"
    assert item.stock_unit.rate == 1
    assert item.stock_unit.selling_price == Decimal("1450.00")
    assert "Jaquar Florentine tap, chrome is saved." in response.content.decode()


@pytest.mark.django_db
def test_an_operator_records_a_service(client, signed_in):
    client.post(
        RECORD,
        submitted(
            name="Tap fitting",
            kind="service",
            hsn_sac="995461",
            stock_unit="OTH",
            selling_price="300",
        ),
    )

    item = Item.objects.get()
    assert item.kind == Item.Kind.SERVICE
    assert item.hsn_sac == "995461"


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["7318", "848180", "39172390"])
def test_goods_take_an_hsn_code_of_4_6_or_8_digits(client, signed_in, code):
    client.post(RECORD, submitted(hsn_sac=code))

    assert Item.objects.get().hsn_sac == code


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["731", "73181", "7318150", "731815000", "73A8"])
def test_goods_with_any_other_code_are_refused(client, signed_in, code):
    response = client.post(RECORD, submitted(hsn_sac=code))

    assert not Item.objects.exists()
    assert "hsn_sac" in response.context["form"].errors


@pytest.mark.django_db
def test_goods_with_a_sac_are_refused(client, signed_in):
    response = client.post(RECORD, submitted(hsn_sac="995461"))

    assert not Item.objects.exists()
    assert "Service" in response.context["form"].errors["hsn_sac"][0]


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["848180", "7318", "99546", "9954611"])
def test_a_service_with_anything_but_a_sac_is_refused(client, signed_in, code):
    response = client.post(RECORD, submitted(kind="service", hsn_sac=code))

    assert not Item.objects.exists()
    assert "hsn_sac" in response.context["form"].errors


@pytest.mark.django_db
@pytest.mark.parametrize("rate", ["0.00", "0.25", "3.00", "5.00", "18.00", "40.00"])
def test_every_current_slab_is_accepted(client, signed_in, rate):
    client.post(RECORD, submitted(gst_rate=rate))

    assert Item.objects.get().gst_rate == Decimal(rate)


@pytest.mark.django_db
@pytest.mark.parametrize("rate", ["12.00", "28.00", "7.00", "-5.00"])
def test_a_rate_that_is_not_a_slab_is_refused(client, signed_in, rate):
    response = client.post(RECORD, submitted(gst_rate=rate))

    assert not Item.objects.exists()
    assert "gst_rate" in response.context["form"].errors


@pytest.mark.django_db
def test_the_rate_is_chosen_from_the_slabs(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert '<select name="gst_rate"' in page
    assert '<option value="18.00">18%</option>' in page
    assert '<option value="12.00">' not in page


@pytest.mark.django_db
def test_the_stock_unit_is_chosen_from_the_gst_unit_codes(client, signed_in):
    page = client.get(RECORD).content.decode()

    assert '<select name="stock_unit"' in page
    assert '<option value="NOS">NOS · Numbers</option>' in page


@pytest.mark.django_db
def test_a_stock_unit_that_is_not_a_gst_unit_code_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(stock_unit="PIECE"))

    assert not Item.objects.exists()
    assert "stock_unit" in response.context["form"].errors


@pytest.mark.django_db
def test_an_item_is_recorded_without_a_price(client, signed_in):
    client.post(RECORD, submitted(selling_price=""))

    assert Item.objects.get().stock_unit.selling_price is None


@pytest.mark.django_db
def test_a_negative_price_is_refused(client, signed_in):
    response = client.post(RECORD, submitted(selling_price="-1"))

    assert not Item.objects.exists()
    assert "selling_price" in response.context["form"].errors


@pytest.mark.django_db
def test_what_recording_requires_is_what_the_form_demands(client, signed_in):
    form = client.get(RECORD).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Item.REQUIRED_TO_RECORD)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("name", "Name"),
        ("kind", "Kind"),
        ("hsn_sac", "HSN/SAC code"),
        ("gst_rate", "GST rate"),
        ("stock_unit", "Stock unit"),
    ],
)
def test_leaving_out_a_required_field_is_refused_naming_it(
    client, signed_in, field, label
):
    response = client.post(RECORD, submitted(**{field: ""}))

    assert not Item.objects.exists()
    assert set(response.context["form"].errors) == {field}
    assert f">{label}</a>" in response.content.decode()


@pytest.mark.django_db
def test_a_refused_submission_keeps_what_was_already_typed(client, signed_in):
    page = client.post(RECORD, submitted(hsn_sac="731")).content.decode()

    assert "Jaquar Florentine tap, chrome" in page
    assert 'value="731"' in page
    assert 'value="1450.00"' in page


@pytest.mark.django_db
def test_recording_assigns_item_codes_in_turn(client, signed_in):
    for name in ("Chrome tap", "Black tap", "White tap"):
        client.post(RECORD, submitted(name=name))

    codes = dict(Item.objects.values_list("name", "code"))
    assert codes == {
        "Chrome tap": "I-0001",
        "Black tap": "I-0002",
        "White tap": "I-0003",
    }


@pytest.mark.django_db
def test_the_next_code_is_one_past_the_highest_assigned(client, signed_in):
    record(name="Old tap", code="I-0041")
    record(name="Older tap", code="I-0007")

    client.post(RECORD, submitted(name="New tap"))

    assert Item.objects.get(name="New tap").code == "I-0042"


@pytest.mark.django_db
def test_the_next_code_counts_past_9999(client, signed_in):
    record(name="Old tap", code="I-9999")
    record(name="Newer tap", code="I-10000")

    client.post(RECORD, submitted(name="New tap"))

    assert Item.objects.get(name="New tap").code == "I-10001"


@pytest.mark.django_db
def test_recording_an_item_names_the_operator_who_did_it(client, signed_in):
    client.post(RECORD, submitted())

    item = Item.objects.get()
    assert item.history.latest().history_user == signed_in
    assert item.stock_unit.history.latest().history_user == signed_in


@pytest.mark.django_db
def test_recording_returns_to_the_item(client, signed_in):
    response = client.post(RECORD, submitted())

    assert response.url == reverse("item_detail", args=[Item.objects.get().pk])


@pytest.mark.django_db
def test_the_form_requires_signing_in(client, business):
    response = client.get(RECORD)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={RECORD}"


@pytest.mark.django_db
def test_the_setup_gate_holds_the_form_shut(client, superuser):
    client.force_login(superuser)

    response = client.post(RECORD, submitted())

    assert response.status_code == 302
    assert response.url == reverse("business_settings")
    assert not Item.objects.exists()


@pytest.mark.django_db
def test_the_setup_gate_holds_the_directory_shut(client, superuser):
    client.force_login(superuser)

    response = client.get(DIRECTORY)

    assert response.status_code == 302
    assert response.url == reverse("business_settings")


@pytest.mark.django_db
def test_an_operator_who_cannot_set_billow_up_is_told_so(client, storekeeper):
    client.force_login(storekeeper)

    response = client.get(DIRECTORY)

    assert "needs setting up" in response.content.decode()


@pytest.mark.django_db
def test_the_setup_gate_holds_an_item_shut(client, superuser):
    item = record()
    client.force_login(superuser)

    response = client.get(reverse("item_detail", args=[item.pk]))

    assert response.status_code == 302
    assert response.url == reverse("business_settings")


@pytest.mark.django_db
def test_a_code_taken_while_recording_moves_on_to_the_next(
    client, signed_in, monkeypatch
):
    record(name="Chrome tap")
    # Another Operator's save landing between reading the highest code and
    # writing this one: the first code offered is already taken.
    offered = iter(["I-0001", "I-0002"])
    monkeypatch.setattr("apps.catalogue.models.next_item_code", lambda: next(offered))

    client.post(RECORD, submitted(name="Black tap"))

    assert Item.objects.get(name="Black tap").code == "I-0002"

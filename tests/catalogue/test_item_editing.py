from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogue.models import Item, ItemUnit
from tests.catalogue.conftest import record, submitted
from tests.conftest import role


def edit_url(item):
    return reverse("edit_item", args=[item.pk])


def detail_url(item):
    return reverse("item_detail", args=[item.pk])


@pytest.mark.django_db
def test_an_operator_changes_an_items_details(client, signed_in, item):
    response = client.post(
        edit_url(item),
        submitted(
            name="Tap fitting",
            kind="service",
            hsn_sac="995461",
            gst_rate="5.00",
            stock_unit="OTH",
            selling_price="300",
        ),
        follow=True,
    )

    item.refresh_from_db()
    assert item.name == "Tap fitting"
    assert item.kind == Item.Kind.SERVICE
    assert item.hsn_sac == "995461"
    assert item.gst_rate == Decimal("5.00")
    assert item.stock_unit.code == "OTH"
    assert item.stock_unit.selling_price == Decimal(300)
    assert Item.objects.count() == 1
    assert ItemUnit.objects.count() == 1
    assert "Tap fitting is saved." in response.content.decode()


@pytest.mark.django_db
def test_the_form_arrives_filled_with_what_is_on_file(client, signed_in, item):
    form = client.get(edit_url(item)).context["form"]

    assert form["name"].value() == "Jaquar Florentine tap, chrome"
    assert form["hsn_sac"].value() == "848180"
    assert form["stock_unit"].value() == "NOS"
    assert form["selling_price"].value() == Decimal("1450.00")


@pytest.mark.django_db
def test_editing_keeps_the_item_code(client, signed_in, item):
    code = item.code

    client.post(edit_url(item), submitted(name="Florentine tap"))

    item.refresh_from_db()
    assert item.code == code


@pytest.mark.django_db
def test_the_price_is_cleared(client, signed_in, item):
    client.post(edit_url(item), submitted(selling_price=""))

    item.refresh_from_db()
    assert item.stock_unit.selling_price is None


@pytest.mark.django_db
def test_what_editing_requires_is_what_recording_requires(client, signed_in, item):
    form = client.get(edit_url(item)).context["form"]

    required = {name for name, field in form.fields.items() if field.required}
    assert required == set(Item.REQUIRED_TO_RECORD)


@pytest.mark.django_db
def test_goods_with_a_sac_are_refused(client, signed_in, item):
    response = client.post(edit_url(item), submitted(hsn_sac="995461"))

    item.refresh_from_db()
    assert item.hsn_sac == "848180"
    assert item.history.count() == 1
    assert "hsn_sac" in response.context["form"].errors


@pytest.mark.django_db
def test_a_refused_edit_leaves_the_unit_and_price_alone(client, signed_in, item):
    client.post(
        edit_url(item),
        submitted(gst_rate="7.00", stock_unit="MTR", selling_price="99"),
    )

    item.refresh_from_db()
    assert item.stock_unit.code == "NOS"
    assert item.stock_unit.selling_price == Decimal("1450.00")


@pytest.mark.django_db
def test_a_negative_price_is_refused(client, signed_in, item):
    response = client.post(edit_url(item), submitted(selling_price="-1"))

    assert "selling_price" in response.context["form"].errors


@pytest.mark.django_db
def test_a_refused_edit_keeps_what_was_typed(client, signed_in, item):
    page = client.post(
        edit_url(item), submitted(name="Florentine tap", hsn_sac="731")
    ).content.decode()

    assert 'value="Florentine tap"' in page
    assert 'value="731"' in page


@pytest.mark.django_db
def test_a_refused_edit_shows_the_name_on_file(client, signed_in, item):
    page = client.post(edit_url(item), submitted(name="")).content.decode()

    assert "<title>Jaquar Florentine tap, chrome · billow</title>" in page


@pytest.mark.django_db
def test_a_change_names_the_operator_who_made_it(client, signed_in, item):
    client.post(edit_url(item), submitted(name="Florentine tap", selling_price="1500"))

    latest = item.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in

    unit = item.stock_unit.history.latest()
    assert unit.history_type == "~"
    assert unit.history_user == signed_in


@pytest.mark.django_db
def test_a_new_stock_unit_names_the_operator_who_chose_it(client, signed_in, item):
    client.post(edit_url(item), submitted(stock_unit="SET"))

    unit = item.stock_unit.history.latest()
    assert unit.code == "SET"
    assert unit.history_user == signed_in


@pytest.mark.django_db
def test_an_unchanged_unit_gains_no_history(client, signed_in, item):
    client.post(edit_url(item), submitted(name="Florentine tap"))

    assert item.stock_unit.history.count() == 1


@pytest.mark.django_db
def test_a_saved_edit_returns_to_the_item(client, signed_in, item):
    response = client.post(edit_url(item), submitted())

    assert response.url == detail_url(item)


@pytest.mark.django_db
def test_the_back_link_returns_to_the_item(client, signed_in, item):
    page = client.get(edit_url(item)).content.decode()

    assert f'href="{detail_url(item)}"' in page


@pytest.mark.django_db
def test_an_item_that_is_not_on_file_is_not_found(client, signed_in):
    response = client.get(reverse("edit_item", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_editing_requires_signing_in(client, item):
    url = edit_url(item)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


@pytest.mark.django_db
def test_the_setup_gate_holds_the_form_shut(client, superuser, item):
    client.force_login(superuser)

    response = client.post(edit_url(item), submitted(name="Florentine tap"))

    item.refresh_from_db()
    assert response.status_code == 302
    assert item.name == "Jaquar Florentine tap, chrome"


@pytest.mark.django_db
def test_without_change_item_editing_is_refused(client, business, powerless, item):
    powerless.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(powerless)

    for response in (
        client.get(edit_url(item)),
        client.post(edit_url(item), submitted(name="Florentine tap")),
    ):
        assert response.status_code == 403
        assert "Can change item" in response.content.decode()

    item.refresh_from_db()
    assert item.name == "Jaquar Florentine tap, chrome"


@pytest.mark.django_db
def test_change_item_through_a_role_edits_an_item(client, business, powerless, item):
    powerless.groups.add(role("Corrector", "catalogue.change_item"))
    client.force_login(powerless)

    assert client.get(edit_url(item)).status_code == 200
    response = client.post(edit_url(item), submitted(name="Florentine tap"))

    assert response.status_code == 302
    item.refresh_from_db()
    assert item.name == "Florentine tap"


@pytest.mark.django_db
def test_the_edit_control_is_hidden_without_change_item(
    client, business, powerless, item
):
    powerless.groups.add(role("Counter", "catalogue.view_item"))
    client.force_login(powerless)

    page = client.get(detail_url(item)).content.decode()

    assert f'href="{edit_url(item)}"' not in page


@pytest.mark.django_db
def test_the_edit_control_is_shown_with_change_item(client, signed_in, item):
    page = client.get(detail_url(item)).content.decode()

    assert f'href="{edit_url(item)}"' in page


@pytest.mark.django_db
def test_the_form_arrives_filled_with_the_item_code(client, signed_in, item):
    form = client.get(edit_url(item)).context["form"]

    assert form["code"].value() == item.code


@pytest.mark.django_db
def test_an_operator_changes_the_item_code(client, signed_in, item):
    client.post(edit_url(item), submitted(code="tap-fl-ch"))

    item.refresh_from_db()
    assert item.code == "TAP-FL-CH"


@pytest.mark.django_db
def test_an_item_keeps_its_own_code_through_an_edit(client, signed_in, item):
    code = item.code

    response = client.post(edit_url(item), submitted(code=code))

    item.refresh_from_db()
    assert response.status_code == 302
    assert item.code == code


@pytest.mark.django_db
def test_leaving_the_item_code_blank_keeps_it(client, signed_in, item):
    code = item.code

    client.post(edit_url(item), submitted(code=""))

    item.refresh_from_db()
    assert item.code == code


@pytest.mark.django_db
def test_another_items_code_is_refused_naming_it(client, signed_in, item):
    record(name="Astral pipe, 110 mm", code="PVC-110")
    code = item.code

    response = client.post(edit_url(item), submitted(code="PVC-110"))

    item.refresh_from_db()
    assert item.code == code
    assert "Astral pipe, 110 mm" in response.context["form"].errors["code"][0]


@pytest.mark.django_db
def test_an_edited_code_of_anything_but_letters_digits_and_hyphens_is_refused(
    client, signed_in, item
):
    response = client.post(edit_url(item), submitted(code="PVC 110"))

    assert "code" in response.context["form"].errors

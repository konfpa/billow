import pytest
from django.urls import reverse

from apps.suppliers.models import Supplier
from tests.conftest import role
from tests.suppliers.conftest import submitted

RECORD = reverse("record_supplier")
DIRECTORY = reverse("supplier_directory")
HOME = reverse("home")


def edit_page(supplier):
    return reverse("edit_supplier", args=[supplier.pk])


def detail_page(supplier):
    return reverse("supplier_detail", args=[supplier.pk])


@pytest.mark.django_db
def test_without_add_supplier_recording_is_refused(client, business, looker):
    client.force_login(looker)

    for response in (client.get(RECORD), client.post(RECORD, submitted())):
        assert response.status_code == 403
        assert "Can add supplier" in response.content.decode()

    assert not Supplier.including_archived.exists()


@pytest.mark.django_db
def test_add_supplier_through_a_role_records_a_supplier(client, business, powerless):
    powerless.groups.add(role("Recorder", "suppliers.add_supplier"))
    client.force_login(powerless)

    assert client.get(RECORD).status_code == 200
    response = client.post(RECORD, submitted())

    assert response.status_code == 302
    assert Supplier.objects.get().name == "Mehta Pipes"


@pytest.mark.django_db
def test_without_change_supplier_editing_is_refused(client, business, looker, supplier):
    client.force_login(looker)

    for response in (
        client.get(edit_page(supplier)),
        client.post(edit_page(supplier), submitted(city="Nashik")),
    ):
        assert response.status_code == 403
        assert "Can change supplier" in response.content.decode()

    supplier.refresh_from_db()
    assert supplier.city == "Pune"


@pytest.mark.django_db
def test_change_supplier_through_a_role_edits_a_supplier(
    client, business, powerless, supplier
):
    powerless.groups.add(role("Corrector", "suppliers.change_supplier"))
    client.force_login(powerless)

    assert client.get(edit_page(supplier)).status_code == 200
    response = client.post(edit_page(supplier), submitted(city="Nashik"))

    assert response.status_code == 302
    supplier.refresh_from_db()
    assert supplier.city == "Nashik"


@pytest.mark.django_db
def test_record_controls_are_hidden_without_add_supplier(client, business, looker):
    client.force_login(looker)

    for url in (HOME, DIRECTORY):
        page = client.get(url).content.decode()

        assert 'data-tip="New Supplier"' not in page, url
        assert f'href="{RECORD}"' not in page, url


@pytest.mark.django_db
def test_record_controls_are_shown_with_add_supplier(client, business, looker):
    looker.groups.add(role("Recorder", "suppliers.add_supplier"))
    client.force_login(looker)

    directory = client.get(DIRECTORY).content.decode()

    assert '<i data-lucide="plus" class="size-4"></i>New Supplier' in directory


@pytest.mark.django_db
def test_suppliers_are_recorded_too_rarely_for_a_quick_action(client, business, looker):
    looker.groups.add(role("Recorder", "suppliers.add_supplier"))
    client.force_login(looker)

    page = client.get(HOME).content.decode()

    assert 'data-tip="New Supplier"' not in page
    assert f'href="{RECORD}"' not in page


@pytest.mark.django_db
def test_edit_control_is_hidden_without_change_supplier(
    client, business, looker, supplier
):
    client.force_login(looker)

    page = client.get(detail_page(supplier)).content.decode()

    assert f'href="{edit_page(supplier)}"' not in page


@pytest.mark.django_db
def test_edit_control_is_shown_with_change_supplier(client, business, looker, supplier):
    looker.groups.add(role("Corrector", "suppliers.change_supplier"))
    client.force_login(looker)

    page = client.get(detail_page(supplier)).content.decode()

    assert f'href="{edit_page(supplier)}"' in page

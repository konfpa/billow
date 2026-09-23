import pytest
from django.urls import reverse

from apps.purchases.models import Purchase, PurchaseLine
from tests.purchases.conftest import line, submitted

RECORD = reverse("record_purchase")


def delete_url(purchase):
    return reverse("delete_purchase", args=[purchase.pk])


@pytest.fixture
def signed_in(client, business, corrector):
    client.force_login(corrector)
    return corrector


@pytest.fixture
def purchase(client, signed_in, supplier, elbow):
    client.post(RECORD, submitted(supplier, line(elbow)))
    return Purchase.objects.get()


@pytest.mark.django_db
def test_a_purchase_entered_by_mistake_is_deleted(client, purchase):
    response = client.post(delete_url(purchase), follow=True)

    assert response.redirect_chain == [(reverse("purchase_directory"), 302)]
    assert not Purchase.objects.exists()
    assert not PurchaseLine.objects.exists()
    assert "Bill MP/2026-27/0412 from Mehta Pipes is deleted." in (
        response.content.decode()
    )


@pytest.mark.django_db
def test_deleting_is_only_ever_a_post(client, purchase):
    assert client.get(delete_url(purchase)).status_code == 405
    assert Purchase.objects.exists()


@pytest.mark.django_db
def test_a_purchase_from_a_supplier_archived_since_is_deleted(
    client, purchase, supplier
):
    supplier.archive()

    client.post(delete_url(purchase))

    assert not Purchase.objects.exists()


@pytest.mark.django_db
def test_deleting_asks_for_confirmation_first(client, purchase):
    page = client.get(reverse("purchase_detail", args=[purchase.pk])).content.decode()

    dialog = page[page.index('role="alertdialog"') :]
    assert "Delete bill MP/2026-27/0412?" in dialog
    assert f'action="{delete_url(purchase)}"' in dialog


@pytest.mark.django_db
def test_a_deletion_is_kept_in_history_naming_who_made_it(client, purchase, signed_in):
    line_on_file = purchase.lines.get()

    client.post(delete_url(purchase))

    deleted = Purchase.history.filter(id=purchase.pk).latest()
    deleted_line = PurchaseLine.history.filter(id=line_on_file.pk).latest()
    assert (deleted.history_type, deleted.history_user) == ("-", signed_in)
    assert (deleted_line.history_type, deleted_line.history_user) == ("-", signed_in)
    assert deleted.bill_number == "MP/2026-27/0412"

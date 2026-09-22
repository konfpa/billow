import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.purchases.models import Purchase
from tests.conftest import PASSWORD
from tests.purchases.conftest import line, submitted

User = get_user_model()

CHANGELIST = reverse("admin:purchases_purchase_changelist")


@pytest.fixture
def purchase(client, signed_in, supplier, elbow):
    client.post(reverse("record_purchase"), submitted(supplier, line(elbow)))
    return Purchase.objects.get()


@pytest.fixture
def superuser_client(client, purchase):
    superuser = User.objects.create_superuser(
        email="priya@example.com", name="Priya Nair", password=PASSWORD
    )
    client.force_login(superuser)
    return client


def change_url(purchase):
    return reverse("admin:purchases_purchase_change", args=[purchase.pk])


@pytest.mark.django_db
def test_the_admin_shows_a_purchase_and_its_lines(superuser_client, purchase):
    page = superuser_client.get(change_url(purchase)).content.decode()

    for detail in ("MP/2026-27/0412", "27AAACM1234K1ZN", "CPVC elbow ¾ inch"):
        assert detail in page
    assert "MP/2026-27/0412" in superuser_client.get(CHANGELIST).content.decode()


@pytest.mark.django_db
def test_the_admin_offers_no_way_to_change_a_purchase(superuser_client, purchase):
    page = superuser_client.get(change_url(purchase)).content.decode()
    superuser_client.post(change_url(purchase), {"bill_number": "FORGED", "_save": ""})

    assert 'name="_save"' not in page
    purchase.refresh_from_db()
    assert purchase.bill_number == "MP/2026-27/0412"


@pytest.mark.django_db
def test_the_admin_cannot_add_or_delete_a_purchase(superuser_client, purchase):
    added = superuser_client.get(reverse("admin:purchases_purchase_add"))
    deleted = superuser_client.post(
        reverse("admin:purchases_purchase_delete", args=[purchase.pk]), {"post": "yes"}
    )

    assert added.status_code == 403
    assert deleted.status_code == 403
    assert Purchase.objects.filter(pk=purchase.pk).exists()


@pytest.mark.django_db
def test_recording_is_kept_in_history_naming_who_recorded_it(
    superuser_client, purchase, buyer
):
    page = superuser_client.get(
        reverse("admin:purchases_purchase_history", args=[purchase.pk])
    ).content.decode()

    assert "Neha Joshi" in page
    assert purchase.history.get().history_user == buyer
    assert purchase.lines.get().history.get().history_user == buyer

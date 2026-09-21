import pytest
from django.urls import reverse

from apps.customers import urls
from apps.customers.models import Customer
from tests.customers.conftest import REGISTERED, submitted

DIRECTORY = reverse("customer_directory")
ARCHIVED = f"{DIRECTORY}?show=archived"


def archive_url(customer):
    return reverse("archive_customer", args=[customer.pk])


def restore_url(customer):
    return reverse("restore_customer", args=[customer.pk])


def detail_url(customer):
    return reverse("customer_detail", args=[customer.pk])


@pytest.mark.django_db
def test_an_operator_archives_a_customer_and_the_row_remains(
    client,
    signed_in,
    customer,
):
    response = client.post(archive_url(customer), follow=True)

    customer.refresh_from_db()
    assert response.status_code == 200
    assert Customer.including_archived.count() == 1
    assert customer.is_archived


@pytest.mark.django_db
def test_an_archived_customer_is_absent_from_the_directory(client, signed_in, archived):
    page = client.get(DIRECTORY).content.decode()

    assert "Sharma Traders" not in page


@pytest.mark.django_db
def test_an_archived_customer_is_visible_under_a_deliberate_filter(
    client,
    signed_in,
    archived,
):
    page = client.get(ARCHIVED).content.decode()

    assert "Sharma Traders" in page
    assert "27AAPFU0939F1ZV" in page


@pytest.mark.django_db
def test_a_customer_on_file_is_absent_from_the_archived_filter(
    client,
    signed_in,
    customer,
):
    page = client.get(ARCHIVED).content.decode()

    assert "Sharma Traders" not in page


@pytest.mark.django_db
def test_an_operator_restores_an_archived_customer(client, signed_in, archived):
    client.post(restore_url(archived))

    archived.refresh_from_db()
    assert not archived.is_archived
    assert archived.gstin == "27AAPFU0939F1ZV"


@pytest.mark.django_db
def test_a_restored_customer_returns_to_the_directory(client, signed_in, archived):
    client.post(restore_url(archived))

    page = client.get(DIRECTORY).content.decode()
    assert "Sharma Traders" in page


@pytest.mark.django_db
def test_a_restored_customer_is_the_same_record(client, signed_in, archived):
    pk = archived.pk

    client.post(restore_url(archived))

    assert Customer.objects.get().pk == pk


@pytest.mark.django_db
def test_archiving_names_the_operator_who_did_it(client, signed_in, customer):
    client.post(archive_url(customer))

    latest = customer.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in
    assert latest.archived_at is not None


@pytest.mark.django_db
def test_restoring_names_the_operator_who_did_it(client, signed_in, archived):
    client.post(restore_url(archived))

    latest = archived.history.latest()
    assert latest.history_type == "~"
    assert latest.history_user == signed_in
    assert latest.archived_at is None


@pytest.mark.django_db
def test_archiving_returns_to_the_customer(client, signed_in, customer):
    response = client.post(archive_url(customer))

    assert response.url == detail_url(customer)


@pytest.mark.django_db
def test_restoring_returns_to_the_customer(client, signed_in, archived):
    response = client.post(restore_url(archived))

    assert response.url == detail_url(archived)


@pytest.mark.django_db
def test_archiving_is_confirmed(client, signed_in, customer):
    page = client.post(archive_url(customer), follow=True).content.decode()

    assert "Sharma Traders is archived." in page


@pytest.mark.django_db
def test_restoring_is_confirmed(client, signed_in, archived):
    page = client.post(restore_url(archived), follow=True).content.decode()

    assert "Sharma Traders is back on file." in page


@pytest.mark.django_db
def test_the_directory_offers_the_archived_filter(client, signed_in, customer):
    page = client.get(DIRECTORY).content.decode()

    assert "show=archived" in page


@pytest.mark.django_db
def test_an_archived_customer_is_reached_from_the_filter(client, signed_in, archived):
    page = client.get(ARCHIVED).content.decode()

    assert detail_url(archived) in page


@pytest.mark.django_db
def test_a_customer_on_file_is_offered_archiving(client, signed_in, customer):
    page = client.get(detail_url(customer)).content.decode()

    assert archive_url(customer) in page
    assert restore_url(customer) not in page


@pytest.mark.django_db
def test_an_archived_customer_is_offered_restoring(client, signed_in, archived):
    page = client.get(detail_url(archived)).content.decode()

    assert restore_url(archived) in page
    assert archive_url(archived) not in page


def test_nothing_in_the_directory_deletes_a_customer():
    """Archiving is the only withdrawal there is; see docs/adr/0008."""
    assert not any("delete" in (pattern.name or "") for pattern in urls.urlpatterns)


@pytest.mark.django_db
def test_archiving_an_archived_customer_leaves_it_as_it_was(
    client,
    signed_in,
    archived,
):
    archived_at = archived.archived_at

    client.post(archive_url(archived))

    archived.refresh_from_db()
    assert archived.archived_at == archived_at
    assert archived.history.count() == 2


@pytest.mark.django_db
def test_restoring_a_customer_on_file_leaves_it_as_it_was(client, signed_in, customer):
    client.post(restore_url(customer))

    customer.refresh_from_db()
    assert not customer.is_archived
    assert customer.history.count() == 1


@pytest.mark.django_db
def test_an_archived_customer_is_still_corrected(client, signed_in, archived):
    client.post(reverse("edit_customer", args=[archived.pk]), submitted(city="Pune"))

    archived.refresh_from_db()
    assert archived.city == "Pune"
    assert archived.is_archived


@pytest.mark.django_db
def test_archiving_is_only_a_post(client, signed_in, customer):
    response = client.get(archive_url(customer))

    customer.refresh_from_db()
    assert response.status_code == 405
    assert not customer.is_archived


@pytest.mark.django_db
def test_archiving_requires_signing_in(client, customer):
    url = archive_url(customer)

    response = client.post(url)

    customer.refresh_from_db()
    assert response.url == f"{reverse('login')}?next={url}"
    assert not customer.is_archived


@pytest.mark.django_db
def test_restoring_requires_signing_in(client, archived):
    url = restore_url(archived)

    response = client.post(url)

    archived.refresh_from_db()
    assert response.url == f"{reverse('login')}?next={url}"
    assert archived.is_archived


@pytest.mark.django_db
def test_the_setup_gate_holds_archiving_shut(client, superuser, customer):
    client.force_login(superuser)

    response = client.post(archive_url(customer))

    customer.refresh_from_db()
    assert response.status_code == 302
    assert not customer.is_archived


@pytest.mark.django_db
def test_a_customer_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.post(reverse("archive_customer", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_gstin_an_archived_customer_holds_says_they_are_archived(
    client,
    signed_in,
    archived,
):
    page = client.post(reverse("record_customer"), submitted()).content.decode()

    assert Customer.including_archived.count() == 1
    assert "Sharma Traders already holds this GSTIN." in page
    assert "They are archived, and can be restored." in page


@pytest.mark.django_db
def test_the_default_manager_leaves_out_the_archived(archived):
    assert not Customer.objects.exists()
    assert Customer.including_archived.get() == archived


@pytest.mark.django_db
def test_reaching_an_archived_customer_is_spelt_out(archived):
    """Forgetting to filter gives the safe answer; see docs/adr/0008."""
    on_file = Customer.objects.create(**{**REGISTERED, "gstin": ""})

    assert list(Customer.objects.all()) == [on_file]
    assert list(Customer.including_archived.archived()) == [archived]

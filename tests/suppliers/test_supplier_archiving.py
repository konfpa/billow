import pytest
from django.urls import reverse

from apps.suppliers import urls
from apps.suppliers.models import Supplier
from tests.suppliers.conftest import REGISTERED, submitted

DIRECTORY = reverse("supplier_directory")
ARCHIVED = f"{DIRECTORY}?show=archived"


def archive_url(supplier):
    return reverse("archive_supplier", args=[supplier.pk])


def restore_url(supplier):
    return reverse("restore_supplier", args=[supplier.pk])


def detail_url(supplier):
    return reverse("supplier_detail", args=[supplier.pk])


@pytest.mark.django_db
def test_an_operator_archives_a_supplier_and_the_row_remains(
    client,
    signed_in,
    supplier,
):
    response = client.post(archive_url(supplier), follow=True)

    supplier.refresh_from_db()
    assert response.status_code == 200
    assert Supplier.including_archived.count() == 1
    assert supplier.is_archived


@pytest.mark.django_db
def test_an_archived_supplier_is_absent_from_the_directory(client, signed_in, archived):
    page = client.get(DIRECTORY).content.decode()

    assert "Mehta Pipes" not in page


@pytest.mark.django_db
def test_an_archived_supplier_is_visible_under_a_deliberate_filter(
    client,
    signed_in,
    archived,
):
    page = client.get(ARCHIVED).content.decode()

    assert "Mehta Pipes" in page
    assert "27AAACM1234K1ZN" in page


@pytest.mark.django_db
def test_a_supplier_on_file_is_absent_from_the_archived_filter(
    client,
    signed_in,
    supplier,
):
    page = client.get(ARCHIVED).content.decode()

    assert "Mehta Pipes" not in page


@pytest.mark.django_db
def test_an_operator_restores_an_archived_supplier(client, signed_in, archived):
    client.post(restore_url(archived))

    archived.refresh_from_db()
    assert not archived.is_archived
    assert archived.gstin == "27AAACM1234K1ZN"


@pytest.mark.django_db
def test_a_restored_supplier_returns_to_the_directory(client, signed_in, archived):
    client.post(restore_url(archived))

    page = client.get(DIRECTORY).content.decode()
    assert "Mehta Pipes" in page


@pytest.mark.django_db
def test_a_restored_supplier_is_the_same_record(client, signed_in, archived):
    pk = archived.pk

    client.post(restore_url(archived))

    assert Supplier.objects.get().pk == pk


@pytest.mark.django_db
def test_archiving_names_the_operator_who_did_it(client, signed_in, supplier):
    client.post(archive_url(supplier))

    latest = supplier.history.latest()
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
def test_archiving_returns_to_the_supplier(client, signed_in, supplier):
    response = client.post(archive_url(supplier))

    assert response.url == detail_url(supplier)


@pytest.mark.django_db
def test_restoring_returns_to_the_supplier(client, signed_in, archived):
    response = client.post(restore_url(archived))

    assert response.url == detail_url(archived)


@pytest.mark.django_db
def test_archiving_is_confirmed(client, signed_in, supplier):
    page = client.post(archive_url(supplier), follow=True).content.decode()

    assert "Mehta Pipes is archived." in page


@pytest.mark.django_db
def test_restoring_is_confirmed(client, signed_in, archived):
    page = client.post(restore_url(archived), follow=True).content.decode()

    assert "Mehta Pipes is back on file." in page


@pytest.mark.django_db
def test_the_directory_offers_the_archived_filter(client, signed_in, supplier):
    page = client.get(DIRECTORY).content.decode()

    assert "show=archived" in page


@pytest.mark.django_db
def test_an_archived_supplier_is_reached_from_the_filter(client, signed_in, archived):
    page = client.get(ARCHIVED).content.decode()

    assert detail_url(archived) in page


@pytest.mark.django_db
def test_a_supplier_on_file_is_offered_archiving(client, signed_in, supplier):
    page = client.get(detail_url(supplier)).content.decode()

    assert archive_url(supplier) in page
    assert restore_url(supplier) not in page


@pytest.mark.django_db
def test_an_archived_supplier_is_offered_restoring(client, signed_in, archived):
    page = client.get(detail_url(archived)).content.decode()

    assert restore_url(archived) in page
    assert archive_url(archived) not in page


def test_nothing_in_the_directory_deletes_a_supplier():
    """Archiving is the only withdrawal there is; see docs/adr/0008."""
    assert not any("delete" in (pattern.name or "") for pattern in urls.urlpatterns)


@pytest.mark.django_db
def test_archiving_an_archived_supplier_leaves_it_as_it_was(
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
def test_restoring_a_supplier_on_file_leaves_it_as_it_was(client, signed_in, supplier):
    client.post(restore_url(supplier))

    supplier.refresh_from_db()
    assert not supplier.is_archived
    assert supplier.history.count() == 1


@pytest.mark.django_db
def test_an_archived_supplier_is_still_corrected(client, signed_in, archived):
    client.post(reverse("edit_supplier", args=[archived.pk]), submitted(city="Nashik"))

    archived.refresh_from_db()
    assert archived.city == "Nashik"
    assert archived.is_archived


@pytest.mark.django_db
def test_archiving_is_only_a_post(client, signed_in, supplier):
    response = client.get(archive_url(supplier))

    supplier.refresh_from_db()
    assert response.status_code == 405
    assert not supplier.is_archived


@pytest.mark.django_db
def test_archiving_requires_signing_in(client, supplier):
    url = archive_url(supplier)

    response = client.post(url)

    supplier.refresh_from_db()
    assert response.url == f"{reverse('login')}?next={url}"
    assert not supplier.is_archived


@pytest.mark.django_db
def test_restoring_requires_signing_in(client, archived):
    url = restore_url(archived)

    response = client.post(url)

    archived.refresh_from_db()
    assert response.url == f"{reverse('login')}?next={url}"
    assert archived.is_archived


@pytest.mark.django_db
def test_the_setup_gate_holds_archiving_shut(client, superuser, supplier):
    client.force_login(superuser)

    response = client.post(archive_url(supplier))

    supplier.refresh_from_db()
    assert response.status_code == 302
    assert not supplier.is_archived


@pytest.mark.django_db
def test_a_supplier_who_is_not_on_file_is_not_found(client, signed_in):
    response = client.post(reverse("archive_supplier", args=[404]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_gstin_an_archived_supplier_holds_says_they_are_archived(
    client,
    signed_in,
    archived,
):
    page = client.post(reverse("record_supplier"), submitted()).content.decode()

    assert Supplier.including_archived.count() == 1
    assert "Mehta Pipes already holds this GSTIN." in page
    assert "They are archived, and can be restored." in page


@pytest.mark.django_db
def test_the_default_manager_leaves_out_the_archived(archived):
    assert not Supplier.objects.exists()
    assert Supplier.including_archived.get() == archived


@pytest.mark.django_db
def test_reaching_an_archived_supplier_is_spelt_out(archived):
    """Forgetting to filter gives the safe answer; see docs/adr/0008."""
    on_file = Supplier.objects.create(**{**REGISTERED, "gstin": ""})

    assert list(Supplier.objects.all()) == [on_file]
    assert list(Supplier.including_archived.archived()) == [archived]


@pytest.mark.django_db
def test_archiving_from_the_directory_returns_to_the_directory(
    client,
    signed_in,
    supplier,
):
    response = client.post(archive_url(supplier), {"next": f"{DIRECTORY}?q=Mehta"})

    assert response.url == f"{DIRECTORY}?q=Mehta"


@pytest.mark.django_db
def test_restoring_from_the_directory_returns_to_the_archived_list(
    client,
    signed_in,
    archived,
):
    response = client.post(restore_url(archived), {"next": ARCHIVED})

    assert response.url == ARCHIVED


@pytest.mark.django_db
def test_archiving_never_follows_a_next_off_the_site(client, signed_in, supplier):
    response = client.post(archive_url(supplier), {"next": "https://evil.example.com/"})

    assert response.url == detail_url(supplier)

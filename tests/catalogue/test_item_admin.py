import pytest
from django.urls import reverse

from apps.catalogue.models import Item


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.mark.django_db
def test_the_admin_lists_items(superuser_client, item):
    page = superuser_client.get(
        reverse("admin:catalogue_item_changelist")
    ).content.decode()

    assert "Jaquar Florentine tap, chrome" in page
    assert "I-0001" in page


@pytest.mark.django_db
def test_the_admin_shows_an_item_with_its_unit_inline(superuser_client, item):
    page = superuser_client.get(
        reverse("admin:catalogue_item_change", args=[item.pk])
    ).content.decode()

    assert "848180" in page
    assert "NOS · Numbers" in page
    assert "1450.00" in page


@pytest.mark.django_db
def test_the_admin_cannot_add_or_delete_an_item(superuser_client, item):
    add = superuser_client.get(reverse("admin:catalogue_item_add"))
    delete = superuser_client.post(
        reverse("admin:catalogue_item_delete", args=[item.pk]), {"post": "yes"}
    )

    assert add.status_code == 403
    assert delete.status_code == 403
    assert Item.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_the_admin_shows_who_created_an_item(superuser_client, superuser):
    item = Item(name="Brass elbow", kind=Item.Kind.GOODS, hsn_sac="7412")
    item._history_user = superuser  # noqa: SLF001 — simple_history's documented hook
    item.save()

    page = superuser_client.get(
        reverse("admin:catalogue_item_history", args=[item.pk])
    ).content.decode()

    assert "Priya Nair" in page

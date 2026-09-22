import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalogue.models import Brand
from tests.catalogue.conftest import record
from tests.conftest import PASSWORD, role

User = get_user_model()

BRANDS = reverse("brand_directory")
RECORD = reverse("record_brand")


def edit_url(brand):
    return reverse("edit_brand", args=[brand.pk])


@pytest.fixture
def cataloguer(db):
    """An Operator who manages Brands, and nothing else."""
    user = User.objects.create_user(
        email="farah@example.com", name="Farah Khan", password=PASSWORD
    )
    user.groups.add(
        role(
            "Cataloguer",
            "catalogue.view_brand",
            "catalogue.add_brand",
            "catalogue.change_brand",
        )
    )
    return user


@pytest.fixture
def managing(client, business, cataloguer):
    client.force_login(cataloguer)
    return cataloguer


@pytest.mark.django_db
def test_an_operator_records_a_brand_on_its_own_page(client, managing):
    response = client.post(RECORD, {"name": "Jaquar"}, follow=True)

    assert Brand.objects.get().name == "Jaquar"
    page = response.content.decode()
    assert "Jaquar is saved." in page
    assert response.redirect_chain[-1][0] == BRANDS


@pytest.mark.django_db
def test_a_brand_needs_a_name(client, managing):
    response = client.post(RECORD, {"name": "  "})

    assert not Brand.objects.exists()
    assert "name" in response.context["form"].errors


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Jaquar", "jaquar", "JAQUAR"])
def test_a_brand_matching_another_regardless_of_case_is_refused(client, managing, name):
    Brand.objects.create(name="Jaquar")

    response = client.post(RECORD, {"name": name})

    assert Brand.objects.count() == 1
    assert response.context["form"].errors["name"] == ["Jaquar is already a Brand."]
    assert f'value="{name}"' in response.content.decode()


@pytest.mark.django_db
def test_an_operator_renames_a_brand(client, managing):
    brand = Brand.objects.create(name="Jaguar")

    response = client.post(edit_url(brand), {"name": "Jaquar"}, follow=True)

    brand.refresh_from_db()
    assert brand.name == "Jaquar"
    assert "Jaquar is saved." in response.content.decode()


@pytest.mark.django_db
def test_a_brand_may_be_renamed_to_its_own_name_in_other_capitals(client, managing):
    brand = Brand.objects.create(name="jaquar")

    client.post(edit_url(brand), {"name": "Jaquar"})

    brand.refresh_from_db()
    assert brand.name == "Jaquar"


@pytest.mark.django_db
def test_renaming_a_brand_onto_another_is_refused(client, managing):
    Brand.objects.create(name="Jaquar")
    brand = Brand.objects.create(name="Astral")

    response = client.post(edit_url(brand), {"name": "JAQUAR"})

    brand.refresh_from_db()
    assert brand.name == "Astral"
    assert response.context["form"].errors["name"] == ["Jaquar is already a Brand."]


@pytest.mark.django_db
def test_the_brands_are_listed_by_name_with_how_many_items_each_has(client, managing):
    jaquar = Brand.objects.create(name="Jaquar")
    Brand.objects.create(name="Astral")
    record(name="Chrome tap", brand=jaquar)
    record(name="Black tap", brand=jaquar)

    response = client.get(BRANDS)

    brands = list(response.context["brands"])
    assert [brand.name for brand in brands] == ["Astral", "Jaquar"]
    page = response.content.decode()
    assert "2 on file" in page
    assert f'href="{edit_url(jaquar)}"' in page


@pytest.mark.django_db
def test_no_brands_says_so(client, managing):
    assert "No Brands yet" in client.get(BRANDS).content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("page", "permission"),
    [
        ("brand_directory", "Can view brand"),
        ("record_brand", "Can add brand"),
        ("edit_brand", "Can change brand"),
    ],
)
def test_the_item_permissions_do_not_open_the_brand_pages(
    client, signed_in, page, permission
):
    brand = Brand.objects.create(name="Jaquar")
    url = reverse(page, args=[brand.pk] if page == "edit_brand" else [])

    response = client.get(url)

    assert response.status_code == 403
    assert permission in response.content.decode()


@pytest.mark.django_db
def test_without_add_brand_recording_a_brand_is_refused(client, business, powerless):
    powerless.groups.add(role("Reader", "catalogue.view_brand"))
    client.force_login(powerless)

    response = client.post(RECORD, {"name": "Jaquar"})

    assert response.status_code == 403
    assert "Can add brand" in response.content.decode()
    assert not Brand.objects.exists()


@pytest.mark.django_db
def test_without_change_brand_renaming_is_refused(client, business, powerless):
    brand = Brand.objects.create(name="Jaquar")
    powerless.groups.add(role("Reader", "catalogue.view_brand"))
    client.force_login(powerless)

    response = client.post(edit_url(brand), {"name": "Astral"})

    assert response.status_code == 403
    assert "Can change brand" in response.content.decode()
    brand.refresh_from_db()
    assert brand.name == "Jaquar"


@pytest.mark.django_db
def test_the_new_brand_control_needs_add_brand(client, business, powerless):
    powerless.groups.add(role("Reader", "catalogue.view_brand"))
    client.force_login(powerless)

    assert f'href="{RECORD}"' not in client.get(BRANDS).content.decode()


@pytest.mark.django_db
def test_the_brand_names_are_links_only_with_change_brand(client, business, powerless):
    brand = Brand.objects.create(name="Jaquar")
    powerless.groups.add(role("Reader", "catalogue.view_brand"))
    client.force_login(powerless)

    page = client.get(BRANDS).content.decode()

    assert "Jaquar" in page
    assert f'href="{edit_url(brand)}"' not in page


@pytest.mark.django_db
def test_the_brands_link_is_shown_with_view_brand(client, managing):
    home = client.get(reverse("home")).content.decode()

    assert f'href="{BRANDS}"' in home
    assert 'data-tip="Brands"' in home


@pytest.mark.django_db
def test_the_brands_link_is_hidden_without_view_brand(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert 'data-tip="Brands"' not in home


@pytest.mark.django_db
def test_the_admin_lists_brands(client, superuser):
    Brand.objects.create(name="Jaquar")
    client.force_login(superuser)

    page = client.get(reverse("admin:catalogue_brand_changelist")).content.decode()

    assert "Jaquar" in page

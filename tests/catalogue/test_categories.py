import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalogue.models import Category
from tests.catalogue.conftest import record
from tests.conftest import PASSWORD, role

User = get_user_model()

CATEGORIES = reverse("category_directory")
RECORD = reverse("record_category")


def edit_url(category):
    return reverse("edit_category", args=[category.pk])


def posted(name, parent=None):
    return {"name": name, "parent": str(parent.pk) if parent else ""}


@pytest.fixture
def cataloguer(db):
    """An Operator who manages Categories, and nothing else."""
    user = User.objects.create_user(
        email="farah@example.com", name="Farah Khan", password=PASSWORD
    )
    user.groups.add(
        role(
            "Cataloguer",
            "catalogue.view_category",
            "catalogue.add_category",
            "catalogue.change_category",
        )
    )
    return user


@pytest.fixture
def managing(client, business, cataloguer):
    client.force_login(cataloguer)
    return cataloguer


@pytest.fixture
def fittings(db):
    return Category.objects.create(name="Fittings")


@pytest.fixture
def elbow(fittings):
    return Category.objects.create(name="Elbow", parent=fittings)


@pytest.mark.django_db
def test_an_operator_records_a_top_level_category(client, managing):
    response = client.post(RECORD, posted("Fittings"), follow=True)

    category = Category.objects.get()
    assert category.name == "Fittings"
    assert category.parent is None
    assert "Fittings is saved." in response.content.decode()
    assert response.redirect_chain[-1][0] == CATEGORIES


@pytest.mark.django_db
def test_an_operator_records_a_category_under_another(client, managing, fittings):
    response = client.post(RECORD, posted("Elbow", fittings), follow=True)

    assert Category.objects.get(name="Elbow").parent == fittings
    assert "Fittings › Elbow is saved." in response.content.decode()


@pytest.mark.django_db
def test_a_category_needs_a_name(client, managing):
    response = client.post(RECORD, posted("  "))

    assert not Category.objects.exists()
    assert "name" in response.context["form"].errors


@pytest.mark.django_db
def test_nesting_under_a_category_that_has_a_parent_is_refused(client, managing, elbow):
    response = client.post(RECORD, posted("Threaded", elbow))

    assert not Category.objects.filter(name="Threaded").exists()
    assert response.context["form"].errors["parent"] == [
        "Elbow is already under Fittings, and Categories go only two levels deep."
    ]


@pytest.mark.django_db
def test_a_category_with_categories_under_it_cannot_go_under_another(
    client, managing, fittings, elbow
):
    pipes = Category.objects.create(name="Pipes")

    response = client.post(edit_url(fittings), posted("Fittings", pipes))

    fittings.refresh_from_db()
    assert fittings.parent is None
    assert response.context["form"].errors["parent"] == [
        "Fittings has Categories under it, and Categories go only two levels deep."
    ]


@pytest.mark.django_db
def test_a_category_cannot_go_under_itself(client, managing, fittings):
    response = client.post(edit_url(fittings), posted("Fittings", fittings))

    fittings.refresh_from_db()
    assert fittings.parent is None
    assert response.context["form"].errors["parent"] == [
        "A Category cannot go under itself."
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Elbow", "elbow", "ELBOW"])
def test_the_same_name_twice_under_one_parent_is_refused(
    client, managing, fittings, elbow, name
):
    response = client.post(RECORD, posted(name, fittings))

    assert Category.objects.filter(parent=fittings).count() == 1
    assert response.context["form"].errors["name"] == [
        "Fittings › Elbow is already a Category."
    ]


@pytest.mark.django_db
def test_the_same_top_level_name_twice_is_refused(client, managing, fittings):
    response = client.post(RECORD, posted("fittings"))

    assert Category.objects.count() == 1
    assert response.context["form"].errors["name"] == [
        "Fittings is already a Category."
    ]


@pytest.mark.django_db
def test_the_same_name_under_different_parents_is_allowed(
    client, managing, fittings, elbow
):
    pipes = Category.objects.create(name="Pipes")

    client.post(RECORD, posted("Elbow", pipes))

    assert Category.objects.filter(name="Elbow").count() == 2


@pytest.mark.django_db
def test_a_child_may_share_its_name_with_a_top_level_category(
    client, managing, fittings
):
    client.post(RECORD, posted("Fittings", fittings))

    assert Category.objects.filter(name="Fittings").count() == 2


@pytest.mark.django_db
def test_an_operator_renames_a_category_and_moves_it(client, managing, fittings):
    tee = Category.objects.create(name="Tea")

    response = client.post(edit_url(tee), posted("Tee", fittings), follow=True)

    tee.refresh_from_db()
    assert tee.name == "Tee"
    assert tee.parent == fittings
    assert "Fittings › Tee is saved." in response.content.decode()


@pytest.mark.django_db
def test_a_category_may_be_renamed_to_its_own_name_in_other_capitals(
    client, managing, fittings
):
    client.post(edit_url(fittings), posted("FITTINGS"))

    fittings.refresh_from_db()
    assert fittings.name == "FITTINGS"


@pytest.mark.django_db
def test_only_top_level_categories_are_offered_as_a_parent(
    client, managing, fittings, elbow
):
    Category.objects.create(name="Pipes")

    page = client.get(RECORD).content.decode()

    assert f'<option value="{fittings.pk}">Fittings</option>' in page
    assert f'value="{elbow.pk}"' not in page


@pytest.mark.django_db
def test_a_category_is_not_offered_as_its_own_parent(client, managing, fittings):
    page = client.get(edit_url(fittings)).content.decode()

    assert f'<option value="{fittings.pk}"' not in page


@pytest.mark.django_db
def test_the_categories_are_listed_each_under_its_parent_with_their_items(
    client, managing, fittings, elbow
):
    pipes = Category.objects.create(name="Pipes")
    tee = Category.objects.create(name="Tee", parent=fittings)
    record(name="Plain elbow", category=elbow)
    record(name="Plain tee", category=tee)
    record(name="Fitting kit", category=fittings)

    response = client.get(CATEGORIES)

    rows = [(str(c), c.item_count) for c in response.context["categories"]]
    assert rows == [
        ("Fittings", 3),
        ("Fittings › Elbow", 1),
        ("Fittings › Tee", 1),
        ("Pipes", 0),
    ]
    page = response.content.decode()
    assert "4 on file" in page
    assert f'href="{edit_url(pipes)}"' in page


@pytest.mark.django_db
def test_no_categories_says_so(client, managing):
    assert "No Categories yet" in client.get(CATEGORIES).content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("page", "permission"),
    [
        ("category_directory", "Can view category"),
        ("record_category", "Can add category"),
        ("edit_category", "Can change category"),
    ],
)
def test_the_item_permissions_do_not_open_the_category_pages(
    client, signed_in, fittings, page, permission
):
    url = reverse(page, args=[fittings.pk] if page == "edit_category" else [])

    response = client.get(url)

    assert response.status_code == 403
    assert permission in response.content.decode()


@pytest.mark.django_db
def test_without_add_category_recording_one_is_refused(client, business, powerless):
    powerless.groups.add(role("Reader", "catalogue.view_category"))
    client.force_login(powerless)

    response = client.post(RECORD, posted("Fittings"))

    assert response.status_code == 403
    assert "Can add category" in response.content.decode()
    assert not Category.objects.exists()


@pytest.mark.django_db
def test_without_change_category_editing_is_refused(
    client, business, powerless, fittings
):
    powerless.groups.add(role("Reader", "catalogue.view_category"))
    client.force_login(powerless)

    response = client.post(edit_url(fittings), posted("Pipes"))

    assert response.status_code == 403
    assert "Can change category" in response.content.decode()
    fittings.refresh_from_db()
    assert fittings.name == "Fittings"


@pytest.mark.django_db
def test_the_category_controls_follow_the_permissions(
    client, business, powerless, fittings
):
    powerless.groups.add(role("Reader", "catalogue.view_category"))
    client.force_login(powerless)

    page = client.get(CATEGORIES).content.decode()

    assert "Fittings" in page
    assert f'href="{RECORD}"' not in page
    assert f'href="{edit_url(fittings)}"' not in page


@pytest.mark.django_db
def test_the_categories_link_is_shown_with_view_category(client, managing):
    home = client.get(reverse("home")).content.decode()

    assert f'href="{CATEGORIES}"' in home
    assert 'data-tip="Categories"' in home


@pytest.mark.django_db
def test_the_categories_link_is_hidden_without_view_category(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert 'data-tip="Categories"' not in home


@pytest.mark.django_db
def test_the_admin_lists_categories(client, superuser, elbow):
    client.force_login(superuser)

    page = client.get(reverse("admin:catalogue_category_changelist")).content.decode()

    assert "Elbow" in page
    assert "Fittings" in page


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Pipes › PVC", "Pipes > PVC"])
def test_a_name_holding_a_path_separator_is_refused(client, managing, name):
    response = client.post(RECORD, posted(name))

    assert not Category.objects.exists()
    assert response.context["form"].errors["name"] == [
        "A name cannot hold › or >, which separate a Category from the one above it."
    ]

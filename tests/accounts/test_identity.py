import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


def test_the_user_model_is_billows_own():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is apps.get_model(settings.AUTH_USER_MODEL)


@pytest.mark.django_db
def test_creating_a_user_stores_the_email_in_lower_case():
    user = User.objects.create_user(
        email="Akshay@Example.COM",
        name="Akshay Prabhu",
        password="a-perfectly-fine-password",
    )

    assert user.email == "akshay@example.com"


@pytest.mark.django_db
def test_an_email_that_differs_only_in_capitalisation_is_taken(operator):
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="Akshay@Example.com", name="Someone Else")


@pytest.mark.django_db
def test_a_user_cannot_be_created_without_an_email():
    with pytest.raises(ValueError, match="email"):
        User.objects.create_user(email="", name="Akshay Prabhu")


@pytest.mark.django_db
def test_a_new_user_is_active_and_holds_no_privileges(operator):
    assert operator.is_active
    assert not operator.is_staff
    assert not operator.is_superuser


@pytest.mark.django_db
def test_a_superuser_holds_every_privilege():
    superuser = User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
        password="a-perfectly-fine-password",
    )

    assert superuser.is_active
    assert superuser.is_staff
    assert superuser.is_superuser


@pytest.mark.django_db
def test_a_user_is_named_as_they_gave_their_name(operator):
    assert operator.get_full_name() == "Akshay Prabhu"
    assert operator.get_short_name() == "Akshay"
    assert str(operator) == "Akshay Prabhu"

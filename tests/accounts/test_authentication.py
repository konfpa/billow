import pytest
from django.contrib.auth import authenticate

from tests.conftest import PASSWORD


@pytest.mark.django_db
def test_an_operator_logs_in_with_their_email_address(operator):
    assert authenticate(email="akshay@example.com", password=PASSWORD) == operator


@pytest.mark.django_db
def test_capitalisation_is_ignored_at_login(operator):
    assert authenticate(email="Akshay@Example.COM", password=PASSWORD) == operator


@pytest.mark.django_db
def test_the_wrong_password_is_refused(operator):
    assert authenticate(email="akshay@example.com", password="wrong") is None


@pytest.mark.django_db
def test_a_deactivated_operator_is_refused(operator):
    operator.is_active = False
    operator.save()

    assert authenticate(email="akshay@example.com", password=PASSWORD) is None

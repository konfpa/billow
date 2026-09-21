import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from apps.customers.models import Customer
from apps.tax.states import State
from tests.business.conftest import COMPLETE

User = get_user_model()

PASSWORD = "a-perfectly-fine-password"

REGISTERED = {
    "name": "Sharma Traders",
    "legal_name": "Sharma Traders LLP",
    "address": "22 Linking Road\nBandra West",
    "city": "Mumbai",
    "postal_code": "400050",
    "state": State.MAHARASHTRA,
    "gstin": "27AAPFU0939F1ZV",
    "email": "accounts@sharma.example.com",
    "phone": "+91 22 5555 0199",
}

# The same PAN registered in a second state, which is a second Customer.
KARNATAKA_GSTIN = "29AAPFU0939F1ZR"


def submitted(**changes):
    """What the form posts: a complete Customer, with anything changed."""
    return {**REGISTERED, **changes}


@pytest.fixture
def operator(db):
    return User.objects.create_user(
        email="akshay@example.com",
        name="Akshay Prabhu",
        password=PASSWORD,
    )


@pytest.fixture
def signed_in(client, operator):
    """An Operator signed in, past the setup gate.

    The directory sits behind the gate like every other page, which
    tests/customers/test_directory.py checks for itself.
    """
    Business.objects.create(**COMPLETE)
    client.force_login(operator)
    return operator


@pytest.fixture
def customer(db):
    return Customer.objects.create(**REGISTERED)


@pytest.fixture
def archived(customer):
    customer.archive()
    return customer


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
        password=PASSWORD,
    )

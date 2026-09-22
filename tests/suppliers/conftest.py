import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.business.conftest import COMPLETE
from tests.conftest import PASSWORD, role

User = get_user_model()


REGISTERED = {
    "name": "Mehta Pipes",
    "legal_name": "Mehta Pipes Private Limited",
    "address": "Plot 14, MIDC\nBhosari",
    "city": "Pune",
    "postal_code": "411026",
    "state": State.MAHARASHTRA,
    "gstin": "27AAACM1234K1ZN",
    "email": "sales@mehtapipes.example.com",
    "phone": "+91 20 5555 0142",
}

# The same PAN registered in a second state, which is a second Supplier.
KARNATAKA_GSTIN = "29AAACM1234K1ZJ"


def submitted(**changes):
    """What the form posts: a complete Supplier, with anything changed."""
    return {**REGISTERED, **changes}


@pytest.fixture
def buyer(db):
    """An Operator who buys for the Business, through a Role."""
    user = User.objects.create_user(
        email="neha@example.com",
        name="Neha Joshi",
        password=PASSWORD,
    )
    purchasing = role(
        "Purchasing",
        "suppliers.view_supplier",
        "suppliers.add_supplier",
        "suppliers.change_supplier",
        "suppliers.archive_supplier",
    )
    user.groups.add(purchasing)
    return user


@pytest.fixture
def signed_in(client, buyer):
    """A buyer signed in, past the setup gate."""
    Business.objects.create(**COMPLETE)
    client.force_login(buyer)
    return buyer


@pytest.fixture
def business(db):
    return Business.objects.create(**COMPLETE)


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(**REGISTERED)


@pytest.fixture
def archived(supplier):
    supplier.archive()
    return supplier


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
        password=PASSWORD,
    )


@pytest.fixture
def looker(powerless):
    """A User who may read Suppliers and do nothing else to them."""
    powerless.groups.add(role("Looker", "suppliers.view_supplier"))
    return powerless

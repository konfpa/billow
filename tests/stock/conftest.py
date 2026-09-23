import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.business.models import Business
from tests.business.conftest import COMPLETE
from tests.conftest import PASSWORD, role
from tests.purchases.conftest import elbow, pipe, submitted, supplier

__all__ = ["elbow", "pipe", "supplier"]

User = get_user_model()

STOCK_START = datetime.date(2026, 4, 1)


@pytest.fixture
def business(db):
    """Counting stock from the start of the financial year."""
    return Business.objects.create(**COMPLETE, stock_start_date=STOCK_START)


@pytest.fixture
def storekeeper(db):
    """An Operator who records Purchases and looks up Items."""
    user = User.objects.create_user(
        email="meera@example.com", name="Meera Iyer", password=PASSWORD
    )
    user.groups.add(
        role(
            "Stores",
            "catalogue.view_item",
            "purchases.view_purchase",
            "purchases.add_purchase",
        )
    )
    return user


@pytest.fixture
def signed_in(client, business, storekeeper):
    client.force_login(storekeeper)
    return storekeeper


def buy(client, supplier, *rows, **changes):
    """Record a Purchase through the form, confirming whatever total it comes to."""
    posted = submitted(supplier, *rows, **changes)
    response = client.post(reverse("record_purchase"), posted)
    if response.status_code == 200 and response.context["form"].total_check:
        check = response.context["form"].total_check
        response = client.post(
            reverse("record_purchase"),
            {**posted, "confirmed_total": check.confirmation},
        )
    assert response.status_code == 302, response.context["form"].errors
    return response

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from apps.catalogue.models import Item, ItemUnit
from apps.tax.rates import GSTRate
from apps.tax.units import UQC
from tests.business.conftest import COMPLETE
from tests.conftest import PASSWORD, role

User = get_user_model()


TAP = {
    "name": "Jaquar Florentine tap, chrome",
    "kind": "goods",
    "hsn_sac": "848180",
    "gst_rate": "18.00",
    "stock_unit": "NOS",
    "selling_price": "1450.00",
}


def units(*rows):
    """The other units as the form posts them.

    Rows on file carry an `id` and come first.
    """
    posted = {
        "units-TOTAL_FORMS": str(len(rows)),
        "units-INITIAL_FORMS": str(sum("id" in row for row in rows)),
    }
    for index, row in enumerate(rows):
        for name, value in row.items():
            posted[f"units-{index}-{name}"] = value
    return posted


def submitted(*rows, **changes):
    """What the form posts: a complete Goods Item, with anything changed."""
    return {**TAP, **units(*rows), **changes}


def record(name="Jaquar Florentine tap, chrome", price="1450.00", **fields):
    """An Item on file with its stock unit, as recording one leaves it."""
    item = Item.objects.create(
        name=name,
        kind=fields.pop("kind", Item.Kind.GOODS),
        hsn_sac=fields.pop("hsn_sac", "848180"),
        gst_rate=fields.pop("gst_rate", GSTRate.EIGHTEEN),
        **fields,
    )
    ItemUnit.objects.create(
        item=item,
        code=UQC.NOS,
        is_stock_unit=True,
        selling_price=Decimal(price) if price else None,
    )
    return item


@pytest.fixture
def business(db):
    return Business.objects.create(**COMPLETE)


@pytest.fixture
def storekeeper(db):
    """An Operator who may look up, record and edit Items, and nothing else."""
    user = User.objects.create_user(
        email="meera@example.com",
        name="Meera Iyer",
        password=PASSWORD,
    )
    user.groups.add(
        role(
            "Storekeeper",
            "catalogue.view_item",
            "catalogue.add_item",
            "catalogue.change_item",
        )
    )
    return user


@pytest.fixture
def signed_in(client, business, storekeeper):
    client.force_login(storekeeper)
    return storekeeper


@pytest.fixture
def item(db):
    return record()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
        password=PASSWORD,
    )

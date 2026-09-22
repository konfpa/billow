import datetime

import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from apps.catalogue.models import Brand, Item, ItemUnit
from apps.suppliers.models import Supplier
from apps.tax.states import State
from tests.business.conftest import COMPLETE
from tests.conftest import PASSWORD, role
from tests.suppliers.conftest import REGISTERED

User = get_user_model()

BILL_DATE = datetime.date(2026, 9, 18)


def lines(*rows):
    """The lines as the form posts them."""
    posted = {"lines-TOTAL_FORMS": str(len(rows)), "lines-INITIAL_FORMS": "0"}
    for index, row in enumerate(rows):
        for name, value in row.items():
            posted[f"lines-{index}-{name}"] = value
    return posted


def line(item, unit="NOS", quantity="10", rate="100.00", **fields):
    return {
        "item": str(item.pk),
        "unit": unit,
        "quantity": quantity,
        "rate": rate,
        **fields,
    }


def submitted(supplier, *rows, **changes):
    """What the form posts: a bill from `supplier`, with anything changed.

    The grand total typed is what one default `line` comes to, from a Supplier
    in the Business's state.
    """
    return {
        "supplier": str(supplier.pk),
        "bill_number": "MP/2026-27/0412",
        "bill_date": BILL_DATE.isoformat(),
        "received_date": BILL_DATE.isoformat(),
        "billed_total": "1180.00",
        **lines(*rows),
        **changes,
    }


def goods(name, code, gst_rate="18.00", brand=None, kind=Item.Kind.GOODS, **units):
    """An Item on file in NOS, and any other units given as code=rate."""
    item = Item.objects.create(
        name=name,
        code=code,
        kind=kind,
        hsn_sac="39174000" if kind == "goods" else "998719",
        gst_rate=gst_rate,
        brand=brand,
    )
    ItemUnit.objects.create(item=item, code="NOS", is_stock_unit=True)
    for unit, rate in units.items():
        ItemUnit.objects.create(item=item, code=unit, rate=rate)
    return item


@pytest.fixture
def business(db):
    return Business.objects.create(**COMPLETE)


@pytest.fixture
def buyer(db):
    """An Operator who records Purchases, through a Role."""
    user = User.objects.create_user(
        email="neha@example.com", name="Neha Joshi", password=PASSWORD
    )
    user.groups.add(
        role("Purchasing", "purchases.view_purchase", "purchases.add_purchase")
    )
    return user


@pytest.fixture
def signed_in(client, business, buyer):
    client.force_login(buyer)
    return buyer


@pytest.fixture
def supplier(db):
    """Mehta Pipes, in Maharashtra as the Business is."""
    return Supplier.objects.create(**REGISTERED)


@pytest.fixture
def karnataka_supplier(db):
    return Supplier.objects.create(
        **{
            **REGISTERED,
            "name": "Kaveri Fittings",
            "state": State.KARNATAKA,
            "gstin": "29AAACM1234K1ZJ",
        }
    )


@pytest.fixture
def unregistered_supplier(db):
    return Supplier.objects.create(
        **{**REGISTERED, "name": "Raju Hardware", "gstin": ""}
    )


@pytest.fixture
def elbow(db):
    brand = Brand.objects.create(name="Astral")
    return goods("CPVC elbow ¾ inch", "ELB-075", brand=brand)


@pytest.fixture
def pipe(db):
    """Stocked in NOS here, and billed by the bundle of 20 as often as not."""
    return goods("PVC pipe 110 mm", "PIPE-110", gst_rate="5.00", BDL="20")

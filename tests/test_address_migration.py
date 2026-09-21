import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

BEFORE = [("business", "0001_initial"), ("customers", "0003_customer_archived_at")]
AFTER = [("business", "0002_address"), ("customers", "0004_address")]

TWO_LINES = {"address_line_1": "14 Marine Drive", "address_line_2": "Nariman Point"}
ONE_LINE = {"address_line_1": "4 Ashok Marg", "address_line_2": ""}


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.fixture
def before_the_change(transactional_db):
    """The schema as it was, restored to the latest once the test is done."""
    apps = migrate(BEFORE)
    yield apps
    migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def seed(apps):
    business = apps.get_model("business", "Business").objects.create(
        pk=1, name="Umbrella Trading", **TWO_LINES
    )
    customers = apps.get_model("customers", "Customer").objects
    two = customers.create(name="Sharma Traders", **TWO_LINES)
    one = customers.create(name="Anita Desai", **ONE_LINE)

    for app, name, row in (
        ("business", "HistoricalBusiness", business),
        ("customers", "HistoricalCustomer", two),
        ("customers", "HistoricalCustomer", one),
    ):
        apps.get_model(app, name).objects.create(
            id=row.pk,
            name=row.name,
            address_line_1=row.address_line_1,
            address_line_2=row.address_line_2,
            created_at=row.created_at,
            updated_at=row.updated_at,
            history_date=timezone.now(),
            history_type="+",
        )


MODELS = (
    ("business", "Business"),
    ("business", "HistoricalBusiness"),
    ("customers", "Customer"),
    ("customers", "HistoricalCustomer"),
)


def stored(apps, *fields):
    return {
        name: sorted(apps.get_model(app, name).objects.values_list(*fields))
        for app, name in MODELS
    }


def test_the_two_lines_become_one_address(before_the_change):
    seed(before_the_change)

    apps = migrate(AFTER)

    joined = ("14 Marine Drive\nNariman Point",)
    single = ("4 Ashok Marg",)
    assert stored(apps, "address") == {
        "Business": [joined],
        "HistoricalBusiness": [joined],
        "Customer": [joined, single],
        "HistoricalCustomer": [joined, single],
    }


def test_the_address_splits_back_into_two_lines(before_the_change):
    seed(before_the_change)
    migrate(AFTER)

    apps = migrate(BEFORE)

    two = ("14 Marine Drive", "Nariman Point")
    one = ("4 Ashok Marg", "")
    assert stored(apps, "address_line_1", "address_line_2") == {
        "Business": [two],
        "HistoricalBusiness": [two],
        "Customer": [two, one],
        "HistoricalCustomer": [two, one],
    }


def test_a_line_too_long_for_the_old_columns_is_not_cut_short(before_the_change):
    apps = migrate(AFTER)
    address = f"{'x' * 300}\nBandra West"
    apps.get_model("customers", "Customer").objects.create(
        name="Sharma Traders", address=address
    )

    apps = migrate(BEFORE)

    row = apps.get_model("customers", "Customer").objects.get()
    assert row.address_line_1 + row.address_line_2 == address

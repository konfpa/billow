import pytest

from apps.business.models import Business
from tests.business.conftest import COMPLETE


@pytest.fixture
def business(db):
    return Business.objects.create(**COMPLETE)


@pytest.fixture
def signed_in(client, business, operator):
    """An Operator signed in, past the setup gate.

    The front door is only reachable once billow knows whose name goes on the
    invoice; the gate itself is tested in tests/business/test_setup_gate.py.
    """
    client.force_login(operator)
    return operator

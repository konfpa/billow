import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from tests.business.conftest import COMPLETE

User = get_user_model()

PASSWORD = "a-perfectly-fine-password"


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

    The front door is only reachable once billow knows whose name goes on the
    invoice; the gate itself is tested in tests/business/test_setup_gate.py.
    """
    Business.objects.create(**COMPLETE)
    client.force_login(operator)
    return operator

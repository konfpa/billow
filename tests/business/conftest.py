import pytest
from django.contrib.auth import get_user_model

from apps.business.models import Business
from apps.tax.states import State
from tests.conftest import PASSWORD

User = get_user_model()


COMPLETE = {
    "name": "Umbrella Trading",
    "legal_name": "Umbrella Trading Private Limited",
    "address": "14 Marine Drive\nNariman Point",
    "city": "Mumbai",
    "postal_code": "400021",
    "state": State.MAHARASHTRA,
    "is_gst_registered": True,
    "gstin": "27AAPFU0939F1ZV",
    "pan": "AAPFU0939F",
    "cin": "U51909MH2012PTC123456",
    "email": "billing@umbrella.example.com",
    "phone": "+91 22 5555 0100",
    "website": "https://umbrella.example.com",
}


@pytest.fixture(autouse=True)
def uploads(settings, tmp_path):
    """Keep an uploaded logo out of the working tree."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def business(db):
    return Business.objects.create(**COMPLETE)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
        password=PASSWORD,
    )

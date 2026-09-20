import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

PASSWORD = "a-perfectly-fine-password"


@pytest.fixture
def operator(db):
    return User.objects.create_user(
        email="akshay@example.com",
        name="Akshay Prabhu",
        password=PASSWORD,
    )

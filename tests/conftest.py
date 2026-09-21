import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()

PASSWORD = "a-perfectly-fine-password"


def role(name, *permissions):
    """A Role holding exactly the permissions named as `app_label.codename`."""
    granted = Group.objects.create(name=name)
    for permission in permissions:
        app_label, codename = permission.split(".")
        granted.permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return granted


@pytest.fixture
def operator(db):
    """An Operator doing their job, through a Role rather than direct grants.

    The Role holds every Customer permission and reading the Business, so the
    suites written before permissions existed still describe an Operator at
    work.
    """
    user = User.objects.create_user(
        email="akshay@example.com",
        name="Akshay Prabhu",
        password=PASSWORD,
    )
    clerk = Group.objects.create(name="Billing clerk")
    clerk.permissions.set(
        Permission.objects.filter(
            content_type__app_label="customers", content_type__model="customer"
        )
        | Permission.objects.filter(
            content_type__app_label="business", codename="view_business"
        )
    )
    user.groups.add(clerk)
    return user


@pytest.fixture
def powerless(db):
    """A User who has been given no Role, and so no work."""
    return User.objects.create_user(
        email="ravi@example.com",
        name="Ravi Kumar",
        password=PASSWORD,
    )

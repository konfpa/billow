import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in

User = get_user_model()


@pytest.mark.django_db
def test_creating_and_changing_a_user_is_recorded(operator):
    operator.name = "Akshay P"
    operator.save()

    records = operator.history.order_by("history_date")

    assert [record.history_type for record in records] == ["+", "~"]
    assert [record.name for record in records] == ["Akshay Prabhu", "Akshay P"]


@pytest.mark.django_db
def test_a_record_names_who_made_the_change(operator):
    superuser = User.objects.create_superuser(
        email="priya@example.com",
        name="Priya Nair",
    )
    operator._history_user = superuser  # noqa: SLF001 — simple_history's documented hook
    operator.name = "Akshay P"
    operator.save()

    assert operator.history.latest().history_user == superuser


@pytest.mark.django_db
def test_no_password_is_copied_into_the_history(operator):
    operator.set_password("another-perfectly-fine-password")
    operator.save()

    assert operator.history.count() == 2
    assert all(not hasattr(record, "password") for record in operator.history.all())


@pytest.mark.django_db
def test_logging_in_leaves_the_history_alone(operator):
    user_logged_in.send(sender=User, request=None, user=operator)

    assert operator.history.count() == 1

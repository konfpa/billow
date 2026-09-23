import datetime

import pytest
from django.urls import reverse

from apps.business.models import Business
from tests.business.conftest import submitted

URL = reverse("business_settings")


@pytest.mark.django_db
def test_a_superuser_sets_the_stock_start_date(client, superuser, business):
    client.force_login(superuser)

    client.post(URL, submitted(stock_start_date="2026-04-01"))

    assert Business.load().stock_start_date == datetime.date(2026, 4, 1)


@pytest.mark.django_db
def test_the_stock_start_date_can_be_moved(client, superuser, business):
    business.stock_start_date = datetime.date(2026, 4, 1)
    business.save()
    client.force_login(superuser)

    client.post(URL, submitted(stock_start_date="2026-07-01"))

    assert Business.load().stock_start_date == datetime.date(2026, 7, 1)


@pytest.mark.django_db
def test_the_stock_start_date_is_optional(client, superuser, business):
    business.stock_start_date = datetime.date(2026, 4, 1)
    business.save()
    client.force_login(superuser)

    client.post(URL, submitted())

    business = Business.load()
    assert business.stock_start_date is None
    assert not business.missing_for_setup()


@pytest.mark.django_db
def test_an_operator_who_may_read_the_business_sees_the_stock_start_date(
    client, operator, business
):
    business.stock_start_date = datetime.date(2026, 4, 1)
    business.save()
    client.force_login(operator)

    page = client.get(URL).content.decode()

    assert "1 April 2026" in page

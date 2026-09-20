import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


@pytest.mark.django_db
def test_healthz_rejects_post(client):
    assert client.post(reverse("healthz")).status_code == 405

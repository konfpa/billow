import pytest
from django.db import OperationalError, connections
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


@pytest.mark.django_db
def test_healthz_rejects_post(client):
    assert client.post(reverse("healthz")).status_code == 405


def test_healthz_reports_503_when_database_is_unreachable(client, monkeypatch):
    def unreachable():
        raise OperationalError

    monkeypatch.setattr(connections["default"], "cursor", unreachable)

    response = client.get(reverse("healthz"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "down"}

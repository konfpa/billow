import pytest


@pytest.mark.django_db
@pytest.mark.urls("tests.core.urls_with_a_bare_refusal")
def test_a_refusal_without_a_permission_attached_names_none(client, signed_in):
    response = client.get("/refused/")

    assert response.status_code == 403
    page = response.content.decode()
    assert "not allowed" in page
    assert "It needs the permission" not in page
    assert "ask one" in page
    assert 'data-kui="app-shell/default"' in page

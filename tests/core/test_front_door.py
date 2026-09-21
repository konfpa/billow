import pytest
from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.urls import reverse

from tests.core.conftest import PASSWORD


@pytest.mark.django_db
def test_the_login_page_is_billows_own(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert "registration/login.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_an_operator_signs_in_with_their_email_address(client, operator):
    response = client.post(
        reverse("login"),
        {"username": "akshay@example.com", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("home")


@pytest.mark.django_db
def test_capitalisation_in_the_address_is_ignored(client, operator):
    response = client.post(
        reverse("login"),
        {"username": "Akshay@Example.COM", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("home")


@pytest.mark.django_db
def test_a_deactivated_user_is_refused(client, operator):
    operator.is_active = False
    operator.save()

    response = client.post(
        reverse("login"),
        {"username": "akshay@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert not response.context["user"].is_authenticated


@pytest.mark.django_db
def test_a_failed_sign_in_does_not_say_which_half_was_wrong(client, operator):
    unknown = client.post(
        reverse("login"),
        {"username": "nobody@example.com", "password": PASSWORD},
    )
    wrong_password = client.post(
        reverse("login"),
        {"username": "akshay@example.com", "password": "not-the-password"},
    )

    assert unknown.context["form"].errors == wrong_password.context["form"].errors


@pytest.mark.django_db
def test_a_failed_sign_in_keeps_the_address_and_says_so_once(client, operator):
    response = client.post(
        reverse("login"),
        {"username": "akshay@example.com", "password": "not-the-password"},
    )
    page = response.content.decode()

    assert page.count("Those details do not match an account.") == 1
    assert 'value="akshay@example.com"' in page
    assert "not-the-password" not in page


@pytest.mark.django_db
def test_an_operator_is_returned_to_the_page_they_asked_for(client, operator):
    response = client.post(
        f"{reverse('login')}?next={reverse('home')}",
        {"username": "akshay@example.com", "password": PASSWORD},
    )

    assert response.url == reverse("home")


@pytest.mark.django_db
def test_an_operator_signs_out(client, signed_in):
    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert not client.get(reverse("home"), follow=True).context["user"].is_authenticated


@pytest.mark.django_db
def test_the_home_page_requires_signing_in(client):
    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={reverse('home')}"


@pytest.mark.django_db
def test_the_home_page_names_who_is_signed_in(client, signed_in):
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert "Akshay Prabhu" in response.content.decode()
    assert "akshay@example.com" in response.content.decode()


@pytest.mark.django_db
def test_every_page_carries_the_same_navigation(client, signed_in):
    home = client.get(reverse("home")).content.decode()

    assert 'aria-label="Main"' in home
    assert reverse("logout") in home


def render_message(level, text):
    return render_to_string(
        "core/messages.html",
        {"messages": [Message(level, text)]},
    )


def test_a_confirmation_is_shown_where_messages_live():
    assert 'id="messages"' in render_message(messages.SUCCESS, "Saved.")


def test_something_to_act_on_is_not_dressed_as_a_confirmation():
    warning = render_message(messages.WARNING, "Two invoices are overdue.")

    assert 'data-lucide="alert-triangle"' in warning
    assert "text-amber-700" in warning
    assert "check-circle-2" not in warning
    assert "text-emerald-600" not in warning


def test_nothing_is_rendered_when_there_is_nothing_to_say():
    assert render_to_string("core/messages.html", {"messages": []}).strip() == ""

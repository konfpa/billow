from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts.forms import EmailAuthenticationForm
from apps.core import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "sign-in/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("sign-out/", auth_views.LogoutView.as_view(), name="logout"),
]

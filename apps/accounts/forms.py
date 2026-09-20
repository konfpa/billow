from django.contrib.auth import forms as auth_forms

from apps.accounts.models import User


class UserCreationForm(auth_forms.UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name")


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

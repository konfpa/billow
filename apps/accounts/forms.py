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


class EmailAuthenticationForm(auth_forms.AuthenticationForm):
    """Django's sign-in form, asking for the address billow knows a User by.

    Only the presentation changes: the field is still `username`, because that
    is what `AuthenticationForm` authenticates with, and folding the address is
    the manager's job rather than the form's.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        # Only the label, because registration/login.html writes its own
        # inputs: widget attributes set here would never reach the page.
        self.fields["username"].label = "Email address"

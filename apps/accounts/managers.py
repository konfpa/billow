from typing import TYPE_CHECKING

from django.contrib.auth.models import BaseUserManager

if TYPE_CHECKING:
    from apps.accounts.models import User


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email: str) -> str:
        """Fold an address whole, rather than only its domain as Django does.

        A User is identified by their email, so `Akshay@example.com` and
        `akshay@example.com` have to be one identity and not two.
        """
        return super().normalize_email(email).lower()

    def get_by_natural_key(self, username: str) -> User:
        return super().get_by_natural_key(self.normalize_email(username))

    def create_user(
        self,
        email: str,
        name: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        if not email:
            msg = "A user must have an email address."
            raise ValueError(msg)

        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        name: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            msg = "A superuser must have is_staff and is_superuser set."
            raise ValueError(msg)

        return self.create_user(email, name, password, **extra_fields)

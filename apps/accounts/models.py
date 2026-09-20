from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from simple_history.models import HistoricalRecords

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Whether this user may reach the Django admin, and nothing more.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # `password` is excluded so that a mistake in one table cannot become a
    # pile of historical credentials; `last_login` so that the trail records
    # changes rather than everyday activity.
    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        constraints = [
            # `save()` folds every address, so the plain unique index above
            # would already be enough for anything the ORM writes. This makes
            # the one-person-one-identity rule structural instead, so a
            # `bulk_create`, a `loaddata` or raw SQL cannot slip past it.
            models.UniqueConstraint(
                Lower("email"),
                name="unique_email_regardless_of_case",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return self.name.split(" ", 1)[0]

    def save(self, *args: object, **kwargs: object) -> None:
        # The one place addresses are folded, so that what is stored and what
        # the unique index compares can never disagree.
        self.email = UserManager.normalize_email(self.email)

        # Excluding `last_login` from the tracked fields keeps it out of the
        # historical columns but not out of the trail: a login still saves the
        # row, and would otherwise file a change record with nothing in it.
        if set(kwargs.get("update_fields") or ()) == {"last_login"}:
            self.skip_history_when_saving = True
            try:
                super().save(*args, **kwargs)
            finally:
                del self.skip_history_when_saving
            return

        super().save(*args, **kwargs)

from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.tax.gstin import validate_gstin, validate_gstin_matches_state
from apps.tax.states import State


class Customer(models.Model):
    """A party billow invoices: one GSTIN, or one unregistered person.

    See docs/adr/0005-a-customer-is-one-registration.md for why a company
    registered in three states is three Customers.
    """

    # Every field is blankable, and what recording a Customer demands is
    # declared here instead. See
    # docs/adr/0004-required-is-validation-not-schema.md.
    REQUIRED_TO_RECORD = (
        "name",
        "address_line_1",
        "city",
        "postal_code",
        "state",
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name the directory is read and searched by.",
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The registered name a tax invoice must carry, if it differs.",
    )

    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(
        max_length=6,
        blank=True,
        validators=[RegexValidator(r"^[1-9][0-9]{5}$", "A PIN code is six digits.")],
    )
    state = models.CharField(
        max_length=2,
        blank=True,
        choices=State,
        help_text=(
            "The state on the address on record, which decides the place of supply."
        ),
    )

    # Blank is an answer here rather than an unfinished one: holding no GSTIN
    # is the whole of what makes a Customer unregistered.
    gstin = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="GSTIN",
        validators=[validate_gstin],
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @property
    def invoice_name(self) -> str:
        """The name a tax invoice carries.

        A Customer trading under its registered name leaves the legal name
        blank, and falls back to the display name rather than storing a copy
        that the two could later disagree about.
        """
        return self.legal_name or self.name

    @property
    def is_registered(self) -> bool:
        """Whether this Customer is invoiced as a B2B supply."""
        return bool(self.gstin)

    def clean(self) -> None:
        super().clean()

        validate_gstin_matches_state(self.gstin, self.state)

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import capfirst
from simple_history.models import HistoricalRecords

from apps.tax.gstin import validate_gstin, validate_gstin_matches_state
from apps.tax.states import State

# billow serves one Business, so its row is always this one. See
# docs/adr/0002-one-business-per-deployment.md.
SINGLETON_PK = 1


class Business(models.Model):
    """The legal entity billow invoices on behalf of. There is exactly one."""

    # Every field is blankable, and what setup demands is declared below
    # instead. See docs/adr/0004-required-is-validation-not-schema.md.
    REQUIRED_FOR_SETUP = (
        "name",
        "address_line_1",
        "city",
        "postal_code",
        "state",
        "is_gst_registered",
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name the Business trades under.",
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
        verbose_name="place of supply",
        help_text="The state that decides CGST plus SGST against IGST.",
    )

    # Three-valued on purpose: unregistered is an answer, unanswered is not.
    is_gst_registered = models.BooleanField(
        null=True,
        default=None,
        verbose_name="GST registered",
    )
    gstin = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="GSTIN",
        validators=[validate_gstin],
    )
    pan = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="PAN",
        validators=[
            RegexValidator(r"^[A-Z]{5}[0-9]{4}[A-Z]$", "A PAN is ten characters."),
        ],
    )
    cin = models.CharField(
        max_length=21,
        blank=True,
        verbose_name="CIN",
        validators=[
            RegexValidator(
                r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$",
                "A CIN is twenty-one characters.",
            ),
        ],
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="business/", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "business"
        constraints = [
            # The one-Business rule made structural, so that a `loaddata`, a
            # `bulk_create` or raw SQL cannot produce a second one and leave
            # billow with two names to put on an invoice.
            models.CheckConstraint(
                condition=models.Q(pk=SINGLETON_PK),
                name="only_one_business",
            ),
        ]

    def __str__(self) -> str:
        return self.name or "The Business"

    def save(self, *args: object, **kwargs: object) -> None:
        # Assigned rather than defaulted, so that an instance built anywhere —
        # a fixture, a shell, a form — writes the one row the check constraint
        # allows instead of failing at the database.
        self.pk = SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> Business:
        """The Business, unsaved and empty when billow has not been set up.

        Later code fetches the Business the way it assumes the database:
        always present, never passed around.
        """
        return cls.objects.filter(pk=SINGLETON_PK).first() or cls()

    @property
    def invoice_name(self) -> str:
        """The name a tax invoice carries.

        A Business trading under its registered name leaves the legal name
        blank, and falls back to the display name rather than storing a copy
        that the two could later disagree about.
        """
        return self.legal_name or self.name

    def missing_for_setup(self) -> tuple[str, ...]:
        """The required fields this Business has not answered yet.

        `False` is an answer, which is why the test is against emptiness
        rather than truth.
        """
        return tuple(
            field
            for field in self.REQUIRED_FOR_SETUP
            if getattr(self, field) in (None, "")
        )

    def what_setup_still_needs(self) -> list[str]:
        """The missing fields, named for a Superuser to read.

        Named from the model rather than from the setup form, so that a
        release which adds a requirement asks for it even before the form
        grows a field for it. See docs/adr/0004-required-is-validation-not-schema.md.
        """
        return [
            capfirst(self._meta.get_field(field).verbose_name)
            for field in self.missing_for_setup()
        ]

    def clean(self) -> None:
        super().clean()

        if self.is_gst_registered and not self.gstin:
            msg = "A GST registered Business has a GSTIN."
            raise ValidationError({"gstin": msg})

        if self.is_gst_registered is False and self.gstin:
            msg = "Remove the GSTIN, or say that the Business is GST registered."
            raise ValidationError({"gstin": msg})

        validate_gstin_matches_state(self.gstin, self.state)

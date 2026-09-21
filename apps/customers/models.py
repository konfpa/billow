from typing import Self

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.tax.gstin import validate_gstin, validate_gstin_matches_state
from apps.tax.states import State


class CustomerQuerySet(models.QuerySet):
    def on_file(self) -> Self:
        """The ordinary directory: everyone still being invoiced."""
        return self.filter(archived_at__isnull=True)

    def archived(self) -> Self:
        """The ones withdrawn from everyday use, reached by asking for them."""
        return self.filter(archived_at__isnull=False)


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

    # When, rather than whether: the history names the Operator who withdrew
    # a Customer, and this answers since when without reading the trail.
    archived_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    objects = CustomerQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        constraints = [
            # One registration is one Customer, made structural so that a
            # `loaddata`, a `bulk_create` or raw SQL cannot put a second
            # Customer behind a GSTIN and leave one taxpayer with two
            # ledgers. Plain uniqueness is enough because a GSTIN is only
            # ever accepted in capitals. Unregistered Customers are exempt:
            # holding no GSTIN is what makes them one, and there may be any
            # number of them.
            models.UniqueConstraint(
                fields=["gstin"],
                condition=~models.Q(gstin=""),
                name="one_customer_per_gstin",
            ),
        ]

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

    @property
    def is_archived(self) -> bool:
        """Whether this Customer is withdrawn from the ordinary directory."""
        return self.archived_at is not None

    def archive(self) -> None:
        """Withdraw this Customer from everyday use, keeping the row.

        See docs/adr/0008-a-customer-is-archived-never-deleted.md.
        """
        if self.is_archived:
            return

        self.archived_at = timezone.now()
        self.save(update_fields=["archived_at", "updated_at"])

    def restore(self) -> None:
        """Return a Customer who came back to the ordinary directory."""
        if not self.is_archived:
            return

        self.archived_at = None
        self.save(update_fields=["archived_at", "updated_at"])

    def clean(self) -> None:
        super().clean()

        validate_gstin_matches_state(self.gstin, self.state)

        if not self.gstin:
            return

        holder = Customer.objects.filter(gstin=self.gstin).exclude(pk=self.pk).first()

        if holder is not None:
            # Named rather than merely refused, so the Operator goes and finds
            # the Customer instead of inventing a near-duplicate — and told
            # where to find one who is archived, since the directory the
            # Operator just searched does not show them.
            msg = f"{holder.name} already holds this GSTIN."
            if holder.is_archived:
                msg = f"{msg} They are archived, and can be restored."
            raise ValidationError({"gstin": msg})

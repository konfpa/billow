from typing import Self

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.fields import AddressField
from apps.tax.gstin import validate_gstin, validate_gstin_matches_state
from apps.tax.states import State


def state_field(help_text: str) -> models.CharField:
    return models.CharField(
        max_length=2,
        blank=True,
        choices=State,
        help_text=help_text,
    )


class CounterpartyQuerySet(models.QuerySet):
    def on_file(self) -> Self:
        """The ordinary directory: everyone still in everyday use."""
        return self.filter(archived_at__isnull=True)

    def archived(self) -> Self:
        """The ones withdrawn from everyday use, reached by asking for them."""
        return self.filter(archived_at__isnull=False)

    def matching(self, query: str) -> Self:
        """Those an Operator could mean by part of a name, or a GSTIN."""
        return self.filter(
            models.Q(name__icontains=query)
            | models.Q(legal_name__icontains=query)
            | models.Q(gstin__icontains=query),
        )


class OnFileManager(models.Manager.from_queryset(CounterpartyQuerySet)):
    """The default manager, which leaves the archived out.

    A picker that forgets to filter is the failure this guards against, so
    forgetting gives the safe answer and reaching an archived one is what has
    to be spelt out. See docs/adr/0008-a-customer-is-archived-never-deleted.md.
    """

    def get_queryset(self) -> CounterpartyQuerySet:
        return super().get_queryset().on_file()


class Counterparty(models.Model):
    """The other side of a supply: one GSTIN, or one unregistered party.

    Customers and Suppliers share this shape today, and each keeps its own
    table, history and GSTIN uniqueness. See
    docs/adr/0005-a-customer-is-one-registration.md for why a company
    registered in three states is three of them.
    """

    # Every field is blankable, and what recording one demands is declared
    # here instead. See docs/adr/0004-required-is-validation-not-schema.md.
    REQUIRED_TO_RECORD = (
        "name",
        "address",
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

    address = AddressField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(
        max_length=6,
        blank=True,
        validators=[RegexValidator(r"^[1-9][0-9]{5}$", "A PIN code is six digits.")],
    )
    # The state is declared by each concrete model through `state_field`, since
    # what it decides differs: the place of supply of a sale, or the input tax
    # of a Purchase.

    # Blank is an answer here rather than an unfinished one: holding no GSTIN
    # is the whole of what makes one unregistered.
    gstin = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="GSTIN",
        validators=[validate_gstin],
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    # When, rather than whether: the history names the Operator who withdrew
    # one, and this answers since when without reading the trail.
    archived_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Declared first, so it is the default manager that the admin, a
    # ModelForm's choices and `get_object_or_404` reach for. Related-object
    # traversal uses Django's own `_base_manager`, which filters nothing, so
    # an invoice can still reach the archived Customer it was issued to.
    objects = OnFileManager()
    including_archived = CounterpartyQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @property
    def invoice_name(self) -> str:
        """The name a tax invoice carries.

        One trading under its registered name leaves the legal name blank, and
        falls back to the display name rather than storing a copy that the two
        could later disagree about.
        """
        return self.legal_name or self.name

    @property
    def is_registered(self) -> bool:
        """Whether input tax credit can be claimed through this one's GSTIN."""
        return bool(self.gstin)

    @property
    def is_archived(self) -> bool:
        """Whether this one is withdrawn from the ordinary directory."""
        return self.archived_at is not None

    def archive(self) -> None:
        """Withdraw from everyday use, keeping the row.

        See docs/adr/0008-a-customer-is-archived-never-deleted.md.
        """
        if self.is_archived:
            return

        self.archived_at = timezone.now()
        self.save(update_fields=["archived_at", "updated_at"])

    def restore(self) -> None:
        """Return one who came back to the ordinary directory."""
        if not self.is_archived:
            return

        self.archived_at = None
        self.save(update_fields=["archived_at", "updated_at"])

    def clean(self) -> None:
        super().clean()

        validate_gstin_matches_state(self.gstin, self.state)

        if not self.gstin:
            return

        # The concrete model's own manager, so a GSTIN on file as a Customer
        # does not stop the same firm being recorded as a Supplier.
        holder = (
            type(self)
            .including_archived.filter(gstin=self.gstin)
            .exclude(pk=self.pk)
            .first()
        )

        if holder is not None:
            # Named rather than merely refused, so the Operator goes and finds
            # the existing one instead of inventing a near-duplicate — and told
            # where to find one who is archived, since the directory the
            # Operator just searched does not show them.
            msg = f"{holder.name} already holds this GSTIN."
            if holder.is_archived:
                msg = f"{msg} They are archived, and can be restored."
            raise ValidationError({"gstin": msg})

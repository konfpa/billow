from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import Counterparty, state_field


class Supplier(Counterparty):
    """A party the Business buys from: one GSTIN, or one unregistered trader.

    Distinct from a Customer even when one firm is both, so the same GSTIN may
    be on file once on each side. See
    docs/adr/0005-a-customer-is-one-registration.md.
    """

    state = state_field(
        "The state on the address on record, which decides whether input tax"
        " on a Purchase is CGST plus SGST or IGST."
    )

    history = HistoricalRecords()

    class Meta(Counterparty.Meta):
        # Apart from change_supplier, so fixing an address does not also let
        # someone withdraw a Supplier. Covers restoring.
        permissions = [("archive_supplier", "Can archive supplier")]
        constraints = [
            # One registration is one Supplier, for the reasons
            # one_customer_per_gstin gives. Nothing relates it to Customers'
            # GSTINs: buying from a firm and selling to it are recorded apart.
            models.UniqueConstraint(
                fields=["gstin"],
                condition=~models.Q(gstin=""),
                name="one_supplier_per_gstin",
            ),
        ]

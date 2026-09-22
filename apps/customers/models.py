from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import Counterparty, state_field


class Customer(Counterparty):
    """A party billow invoices: one GSTIN, or one unregistered person.

    See docs/adr/0005-a-customer-is-one-registration.md for why a company
    registered in three states is three Customers.
    """

    state = state_field(
        "The state on the address on record, which decides the place of supply."
    )

    history = HistoricalRecords()

    class Meta(Counterparty.Meta):
        # Apart from change_customer, so fixing an address does not also
        # let someone withdraw a Customer from invoicing. Covers restoring.
        permissions = [("archive_customer", "Can archive customer")]
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

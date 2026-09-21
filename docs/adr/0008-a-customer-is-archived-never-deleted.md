# A Customer is archived, never deleted

A Customer who stops buying is withdrawn from the ordinary directory by
stamping `archived_at`, and the row stays. Nothing in billow deletes a
Customer, and the archived ones are reached by asking for them.

## Considered Options

Deleting the row is the obvious withdrawal and is wrong twice over. An invoice
already issued names its recipient, and ADR 0007 keeps that name on the invoice
itself — but the link back to the Customer is what groups and reports a
buyer's history, and deleting breaks it. And a buyer who returns after two
years is the same Customer they were before, which a deleted row cannot say:
the Operator records a second one, and one taxpayer ends up with two ledgers.

Hiding the archived ones entirely would make the second case worse rather than
better, because an Operator checking whether a returning buyer is already on
file would find nothing. Hence a filter rather than a disappearance.

## Consequences

Every query that lists Customers to choose from must ask for `on_file()`
rather than `all()`, and a query that forgets will offer an archived Customer
for invoicing. Archiving is not a soft delete to be swept up by a purge job:
there is no purge.

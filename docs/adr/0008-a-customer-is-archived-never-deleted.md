# A Customer is archived, never deleted

A Customer who stops buying is withdrawn from the ordinary directory by
stamping `archived_at`, and the row stays. Nothing in billow deletes a
Customer. The default manager leaves the archived ones out, so reaching them
is something a query has to spell out: `Customer.including_archived`.

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

Filtering the default manager is the one place Django's own advice is set
aside deliberately. The alternative, an opt-in `on_file()` on an unfiltered
default, puts the whole rule on every future author remembering it, and the
release where one forgets offers an archived Customer to invoice. Forgetting
now gives the safe answer instead.

What this costs is that the default manager no longer speaks for the table.
`Customer.objects.count()` is not how many Customers there are, and anything
that must see every row — the duplicate-GSTIN check, the edit page, restoring
— names `including_archived` and is easy to leave out by accident. Related
traversal is unaffected: Django's `_base_manager` filters nothing, so an
invoice still reaches the archived Customer it was issued to.

Archiving is not a soft delete to be swept up by a purge job: there is no
purge.

# An issued Invoice is cancelled, never edited or deleted

An Invoice is frozen from the moment it is issued. A wrong one is Cancelled:
it keeps its number and every detail it was issued with, it is marked with a
reason, who cancelled it and when, and its Stock movements are withdrawn. The
sale is then issued again as a new Invoice. The admin shows Invoices
read-only, even to a Superuser.

## Considered Options

ADR 0013 lets a Purchase be edited in place, and doing the same here would
be simpler for the Operator who typed a quantity wrong. That rule works
because the Supplier's paper is the document of record. An Invoice *is* the
document of record: the customer holds a copy, and the Business reports it
in GSTR-1. An edit makes billow disagree with the paper in the customer's
hand, and a deletion leaves a gap in a series that Rule 46 requires to be
consecutive. Letting a Superuser edit in the admin was also rejected. It is
the same edit with fewer checks, and its Stock movements would not follow it.

## Consequences

Numbers are never reused and never missing. A cancelled number stays in the
series and is reported as cancelled. Correcting part of a sale after the fact,
such as goods returned or an overcharge, is not a cancellation but a credit
note, which is a separate document with its own series.

## The cancellation window

An Invoice may be Cancelled only until the 10th of the month after its date.
After that, the month's GSTR-1 (due on the 11th) may already hold it, and a
correction belongs on a credit note. billow does not know when the return was
filed, so it follows the filing calendar rather than asking.

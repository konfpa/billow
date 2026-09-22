# A Purchase is corrected in place, and may be deleted

A Purchase is a copy of a bill the Supplier issued, so an Operator who typed it
wrong edits it, and one entered twice or against the wrong Supplier is deleted.
Its Stock movements follow the edit or go with it, and the history rows keep
what it said before.

## Considered Options

ADR 0007 freezes an invoice once issued, and corrects it only by a credit note,
and applying the same rule to Purchases reads as consistent. That rule exists
because the Business filed the invoice in a return; nothing about a Purchase is
filed from billow, and the document of record is the Supplier's. Reversing
entries for a typo would leave two Purchases for one bill, and the bill number,
unique per Supplier per financial year, could not be entered correctly again.

## Consequences

A Purchase's Stock movements are derived from its lines and rewritten when they
change, so stock on hand for a past date can change after the fact. A return of
goods to a Supplier is not a deletion or an edit; it is a debit note, a
separate document that billow does not yet record.

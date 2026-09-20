# An invoice stores its own copy of the recipient's details

The name, address, state and GSTIN printed on an invoice are copied onto the
invoice when it is issued. The link to the Customer remains, for grouping and
reporting, but nothing rendered comes through it.

## Considered Options

Rendering from the Customer record keeps one copy of the truth, and is wrong
for this document: an issued invoice has been filed in a return, and a customer
who moves office in March must not silently rewrite the January invoice that
was filed against the old address.

Reconstructing the Customer as it stood at issue time from its history rows
gives the right answer and still fails, because it makes every reprint depend
on the audit trail being intact and complete. History exists to answer who
changed what; an invoice that cannot be reprinted without it has made an audit
convenience load-bearing.

## Consequences

Recipient fields appear on both the Customer and the invoice, which reads as
denormalisation to be tidied up, and is not. Correcting a Customer does not
correct invoices already issued to them, which is the point: a wrongly issued
invoice is corrected by a credit note, not by an edit.

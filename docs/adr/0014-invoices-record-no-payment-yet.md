# An invoice records what was sold, not how it was paid

For now, an Invoice records only the sale: the recipient, the lines, the tax and
the total. It records nothing about tender. No cash, UPI or card, no split, no
change due, no amount outstanding and no credit sale. Every Invoice is simply
what the Business charged.

## Considered Options

ADR 0012 says billow records payments received against invoices, and tender
at the counter reads like the natural first half of that promise: modes, a
split and change due. The second half follows at once, though. The first
contractor who takes goods on credit needs an amount due, a later receipt
against it and a Customer balance. That makes a receivables ledger, and a
half-built ledger drifts from the accounts faster than none. Recording tender
without balances also invites the question "who still owes us?", which billow
could then only answer wrongly.

## Consequences

The promise in ADR 0012 still stands but is not yet delivered: payments
received are a later piece of work, designed with credit sales, receipts and
balances together. Until then the counter screen issues an Invoice rather than
taking payment. Rules about how a sale is paid, such as the ban on receiving
₹2 lakh or more in cash under s.269ST of the Income-tax Act, are not enforced by
billow. A contributor who adds a "paid" flag to finish the job is re-opening
this decision and should do so deliberately.

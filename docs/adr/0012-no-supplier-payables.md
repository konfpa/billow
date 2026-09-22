# billow keeps no payables

billow records what the Business buys for stock and input tax, and nothing
about what it owes. A Purchase carries no amount outstanding, due date or
payment status, a Supplier carries no credit period, bank account or Udyam
registration, and there is no Supplier ledger. Paying Suppliers, and knowing
what is still owed to them, belongs to the accounting system the Business
already runs.

## Considered Options

Tracking payables while payments happen elsewhere — a balance per Supplier and
a "paid" mark per Purchase — reads as the natural completion of recording a
Supplier's bill. It makes billow a second, hand-kept copy of a ledger the
accounts already hold, which drifts the first time a payment is recorded in
one and not the other. It also pulls in what payables carry with them: due
dates, the 45-day MSME rule under section 43B(h), and bank details that are
the target of changed-account fraud. None of these is billing.

## Consequences

Purchases will look unfinished to a contributor who expects a balance next to
every bill, and adding one "to finish the job" is the change this record
exists to prevent. Supplier and Customer are therefore not symmetric: billow
records payments received against invoices, and never payments made.

# A Customer is one GST registration, not one company

A Customer holds at most one GSTIN, so a company registered in three states is
three Customers rather than one company with three registrations chosen between
at invoice time. Unregistered Customers are the same shape with the GSTIN left
empty, because whether the Customer is a person or an organisation changes
nothing billow prints or computes.

## Considered Options

Modelling the legal entity and hanging registrations off it reads as the more
faithful picture, and it is the one an operator describes in conversation. It
does not survive contact with the invoice: CGST section 25(4) and (5) make each
registration a distinct person, so the state, the place of supply, the reported
GSTR-1 line and the ledger all belong to the registration and none of them
belong to the entity. The entity shape therefore makes every invoice ask which
registration it means, and answers with a join.

Grouping the siblings under a shared PAN is the piece the entity shape gets
right, and it is additive: a group can be introduced later without touching an
invoice. Splitting a merged record afterwards is a migration through data
nobody can reconstruct.

## Consequences

The Customer list holds near-duplicate names that differ only by state, which
looks like a bug and is not. The GSTIN is unique and the name deliberately is
not, so duplicate detection cannot lean on the name.

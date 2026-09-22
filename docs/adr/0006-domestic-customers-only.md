# billow invoices domestic customers only

Exports, supplies to SEZ units and developers, deemed exports, UIN holders,
Input Service Distributor registrations and government TDS deductors are all
out of scope, deliberately. billow invoices customers who are registered under
GST in India, or not registered at all.

## Considered Options

Each of these reads like a field and is a tax path. An export invoice is
zero-rated and carries a shipping bill, port code, country of destination,
currency and the LUT number, and starts the rule 96A clock that withdraws the
LUT when realisation is late. An SEZ supply is IGST whatever the state codes
say, but only for authorised operations, and needs the letter of approval and
its validity. A deemed export is not zero-rated at all, is goods only, and is
proved by the recipient's endorsement on a form billow does not hold. A UIN
holder is not a registered person yet its UIN is mandatory on the invoice. An
ISD registration may be billed for input services and never for goods. A
government deductor's threshold is measured per contract, which is a concept
billow has no record of.

Supporting one of these halfway is worse than not supporting it. An operator
who knows billow cannot raise an export invoice raises it elsewhere; an
operator handed a form that accepts a country produces a document that looks
right and is not, and under rule 48(5) an invoice that does not comply is not
an invoice, which destroys the recipient's input tax credit rather than the
issuer's.

## Consequences

A Business that starts exporting cannot record it in billow, which is the
intended answer until export is designed as its own piece of work. The absence
must stay visible: billow should not grow a field that half-admits one of these
customers.

## Suppliers

The same holds on the buying side. Imports and purchases from SEZ units are
out of scope: an import is taxed at customs on a Bill of Entry, with IGST paid
there and claimed against the bill rather than an invoice, and its supplier
has neither a GSTIN nor an Indian state. Every Supplier is registered under
GST in India, or not registered at all.

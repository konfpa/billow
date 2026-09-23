# billow serves Businesses below the e-invoicing threshold

billow does not generate an IRN or print the signed QR code of GST e-invoicing,
and it serves Businesses whose aggregate turnover keeps them outside it
(₹5 crore today). The Business settings record whether the Business is required
to e-invoice. A Business that is required to cannot issue an Invoice to a
Registered customer from billow, and is told why.

## Considered Options

Deferring e-invoicing silently, like e-way bills, GSTR-1 export and
multi-counter billing, reads as the same kind of deferral. It is not. The
others cost the Business some convenience. A B2B invoice issued without an IRN
by a Business that is required to e-invoice is not an invoice at all under
Rule 48(5). It destroys the *buyer's* input tax credit, the same failure ADR
0006 refuses to risk with half-supported customers. Building e-invoicing now
means integrating with the IRP through a GSP, holding API credentials and
handling cancellation within 24 hours. That is a project of its own for a
threshold the target Business does not reach.

## Consequences

Sales to Unregistered customers and Counter sales stay open to a Business that
e-invoices, since e-invoicing covers only B2B. A Business that grows past the
threshold keeps billow for retail and bills Registered customers elsewhere,
until e-invoicing is designed as its own piece of work.

# Tax registration is modelled for India, explicitly

The Business stores `gstin`, `pan`, `cin` and a `state` chosen from the GST
state codes, rather than a country-neutral tax identifier. A GSTIN is
validated in full — the 15-character checksum, and a cross-check that the
state code it embeds matches the Business's own state.

## Considered Options

A generic shape — a list of tax registrations, each a type and a string — costs
nothing today and reads as the responsible choice. It stops reading that way at
the first invoice: deciding CGST plus SGST against IGST needs the place of
supply as an enum, and a tax number nobody validates is a typo that is copied
onto every invoice ever issued. Generic would have to be un-generalised the
moment tax is actually computed, so the abstraction is deferred until a second
jurisdiction exists to abstract over.

## Consequences

Supporting a second country means new columns and a real conversation about
tax, not a configuration change. `is_gst_registered` is a stored answer rather
than an inference from a blank GSTIN, so that a Business below the registration
threshold is distinguishable from a form nobody finished.

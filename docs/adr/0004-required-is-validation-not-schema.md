# Required is a validation rule, not a schema one

Fields the setup page demands are declared on the model as a list the form and
the setup gate both read, while the columns themselves stay nullable or
blankable. A release that adds a requirement adds it to that list; the gate
then closes by itself for every Business saved under the older rules, and the
operator is asked for the missing field on next sign-in.

## Considered Options

Making newly required fields `NOT NULL` needs a backfill for the rows that
predate them, and the only values available are invented ones — a placeholder
GSTIN is worse than a blank, because it is indistinguishable from an answer.
Stamping a version on the row and comparing it against a constant works, but
relies on someone remembering the bump in the release that needed it; the
release where they forget ships invoices missing a legally required field.

## Consequences

A contributor reading the migrations will find columns that look optional but
cannot be left empty, and may try to tighten them — hence this record. Rows
that are complete today may be incomplete after an upgrade, which is the
intent: incompleteness is a state billow is designed to notice and ask about,
not an error condition.

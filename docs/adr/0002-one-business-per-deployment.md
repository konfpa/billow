# One Business per deployment

billow serves exactly one Business: the legal entity it invoices on behalf of.
That Business is a single row, held to one by a check constraint on the primary
key, and no Customer, Invoice or setting carries a tenancy foreign key. An
installation that must bill for two entities runs twice.

## Considered Options

Multi-tenancy — Users belonging to Businesses, every later table scoped by a
`business` column — is the shape that is expensive to add afterwards, which is
the usual argument for adding it up front. The argument loses here because
billow is self-hosted and deployed per business, so tenancy would be paid for
on every table and every query while always holding one row. The escape hatch
is a second deployment, not a migration.

## Consequences

Every later model may assume the Business the way it assumes the database: one,
always present, fetched rather than passed. Reversing this is a migration
across every table billow will ever have, so the assumption is worth stating
once here rather than rediscovering it per model.

# Items are flat: a variant is its own Item

Every finish, size and type of a thing the Business sells is its own Item. A
chrome and a matte-black Florentine tap are two Items, and so is every
size-and-type combination of an elbow that is actually stocked. Nothing groups
Items into a parent with children. Selling one thing in several units, such as
a pipe by the piece or by the foot, is handled by units on the Item rather than
by variants.

## Considered Options

Parent Items with attribute-generated children read as the natural model for a
hardware catalogue, and they save typing when many combinations are created at
once. They put a second question on every rule: whether price, HSN, GST rate,
unit and code belong to the parent or the child, and whether a child may
override them. Stock, cost and barcodes belong to the child regardless, since
that is what is counted and scanned, so the parent adds rules without holding
anything. The Business's typical catalogue is a handful of finishes per model,
where the typing saved is small.

Grouping is additive: it can be laid over existing Items later without touching
an invoice or a stock movement. Splitting a parent/child model back into
independent Items is a migration through every price and movement.

## Consequences

Creating many combinations is a job for creation tooling, such as duplicating
an Item or generating several at once, which leaves only flat Items behind.
Finding related Items relies on consistent names, Brand and Category rather
than on a parent.

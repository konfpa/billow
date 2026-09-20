# billow

Billing software: the people who run a business's invoicing, and the customers
they invoice.

## Language

**User**:
A person who authenticates with billow. Identified by their email address.
_Avoid_: Account, login, member

**Operator**:
A User in their working role — the human who issues invoices, records payments
and otherwise runs billing. Every User is an operator today.
_Avoid_: Staff, agent, admin

**Customer**:
A person or organisation that billow invoices. Never authenticates and holds no
credentials, and so is not a User.
_Avoid_: Client, account, payer

**Deactivated**:
A User who may no longer authenticate, but whose record remains. Distinct from
deleted: a User is never deleted, because the audit trail names them as the
actor behind past changes.
_Avoid_: Disabled, removed, archived

**Superuser**:
A User holding every permission unconditionally, and the only one who creates
other Users.
_Avoid_: Owner, root

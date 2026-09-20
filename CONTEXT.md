# billow

Billing software: the people who run a business's invoicing, and the customers
they invoice.

## Language

**User**:
A person who authenticates with billow. Identified by their email address.
_Avoid_: Account, login, member

**Operator**:
A User in their working role — the human who issues invoices, records payments
and otherwise runs billing on behalf of the Business. Every User is an operator
today.
_Avoid_: Staff, agent, admin

**Customer**:
A party billow invoices: one GSTIN, or one unregistered person. A company
registered in three states is three Customers, because GST treats each
registration as a distinct person and each one is billed, taxed and reported
separately. Never authenticates and holds no credentials, and so is not a User.
_Avoid_: Client, account, payer

**Address on record**:
The one address billow holds for a Customer, which decides the place of supply
when nothing on the invoice says otherwise. Distinct from an address of
delivery, which belongs to a single supply rather than to the Customer.
_Avoid_: Billing address, registered address, primary address

**Archived**:
A Customer withdrawn from everyday use: absent from the pickers an Operator
chooses from, but still named by every invoice already issued to them. Distinct
from Deactivated, which is about a User's ability to authenticate.
_Avoid_: Deleted, inactive, disabled, hidden

**Deactivated**:
A User who may no longer authenticate, but whose record remains. Distinct from
deleted: a User is never deleted, because the audit trail names them as the
actor behind past changes.
_Avoid_: Disabled, removed, archived

**Superuser**:
A User holding every permission unconditionally, and the only one who creates
other Users.
_Avoid_: Owner, root

**Business**:
The single legal entity billow invoices on behalf of, and whose name, address
and tax registration appear on every invoice. Exactly one exists per
deployment.
_Avoid_: Company, Organisation, Tenant, Merchant

**Legal name**:
The Business's registered name, which a tax invoice must carry. Distinct from
the display name it trades and letterheads under, which is often shorter.
_Avoid_: Registered name, trading name, entity name

**Place of supply**:
The state that decides whether a supply is taxed as CGST plus SGST or as IGST.
_Avoid_: Tax state, supply state, region

**Setup gate**:
What billow closes over itself until the Business holds every detail it
requires today: a Superuser lands back on the setup page, and an Operator who
is not one is told billow needs setting up. Judged against what the current
release requires, so a Business recorded under older rules becomes incomplete
again when a later release asks for more.
_Avoid_: Onboarding, wizard, first-run

**GST registered**:
Whether the Business holds a GSTIN, and so issues tax invoices rather than
bills of supply. A Business below the registration threshold is not, and that
is a deliberate answer rather than an unfinished one.
_Avoid_: Taxable, registered, GST enabled

**Registered customer**:
A Customer that holds a GSTIN, and so is invoiced as a B2B supply that the
recipient claims input tax credit against.
_Avoid_: B2B customer, business customer, taxable customer

**Unregistered customer**:
A Customer holding no GSTIN, whether a private individual or a business below
the registration threshold. The absence of a GSTIN is the whole distinction;
whether the Customer is a person or an organisation is not one billow draws.
_Avoid_: B2C customer, consumer, retail customer, individual

**Counter sale**:
An invoice raised against no Customer at all, for a walk-in buyer nobody
records. Distinct from a sale to an Unregistered customer, who is recorded and
can be invoiced again.
_Avoid_: Walk-in customer, cash sale, anonymous customer, guest

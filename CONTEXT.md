# billow

Billing software: the people who run a business's invoicing, and the customers
they invoice.

## Language

**User**:
A person who authenticates with billow. Identified by their email address.
_Avoid_: Account, login, member

**Operator**:
A User in their working role — the human who issues invoices, records payments
and otherwise runs billing on behalf of the Business. An Operator does only
the work they have been granted; being a User grants none of it.
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
A Customer, Supplier or Item withdrawn from everyday use: absent from the
pickers an Operator chooses from, but still named by every invoice, Purchase
and stock movement that already refers to it. Distinct
from Deactivated, which is about a User's ability to authenticate.
_Avoid_: Deleted, inactive, disabled, hidden

**Deactivated**:
A User who may no longer authenticate, but whose record remains. Distinct from
deleted: a User is never deleted, because the audit trail names them as the
actor behind past changes.
_Avoid_: Disabled, removed, archived

**Role**:
A named set of work that a Superuser grants to Operators, such as recording
Customers or archiving them. An Operator's access is the sum of their Roles.
_Avoid_: Group, profile, access level

**Superuser**:
A User holding every permission unconditionally, and the only one who creates
other Users, defines Roles and grants them.
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

**Item**:
One thing the Business sells, described once so it can be invoiced and
stocked without retyping: a name, whether it is goods or a service, its HSN or
SAC code and its GST rate. A chrome and a matte-black finish of the same tap
are two Items, because each is sold, priced and counted on its own.
_Avoid_: Product, article, SKU, stock item

**Goods**:
An Item that is a physical thing, classified by an HSN code and counted in
stock.
_Avoid_: Product, material, merchandise

**Service**:
An Item that is work rather than a thing, such as fitting or delivery,
classified by a SAC code and never counted in stock.
_Avoid_: Labour, charge, job

**One-off line**:
An invoice line typed straight onto the invoice with its own name, code, rate
and price, for something the Business has no Item for. It leaves the catalogue
untouched.
_Avoid_: Misc item, ad hoc item, custom line, free-text line

**Stock unit**:
The one unit an Item's stock is counted in, such as feet for a pipe bought by
the piece. Every other unit the Item is bought or sold in is defined once, as a
fixed rate against it, so any unit converts to any other through it.
_Avoid_: Base unit, primary unit, UOM

**GST unit code**:
The code a GST return reports a quantity in, such as NOS, MTR or SQF, from the
fixed list GST publishes (the UQC). A unit billow offers that has no code of
its own, such as feet, reports under one by an exact factor (1 ft = 0.3048
MTR), while the invoice and stock keep the unit the Operator chose. Units of
different kinds, such as feet and square feet, never convert into each other;
only an Item's own rates link them.
_Avoid_: UOM, unit of measure

**Supplier**:
A party the Business buys from: one GSTIN, or one unregistered trader, in
India. Distinct from a Customer even when one firm is both, because a sale and
a purchase are taxed and reported separately whoever the other party is; the
same GSTIN may then be on file once on each side.
_Avoid_: Vendor, seller, party

**Purchase**:
A Supplier's bill recorded in billow, whose lines bring Goods into stock at a
cost. Identified by the Supplier and the bill number printed on it, which the
Supplier may not repeat within a financial year. A copy of someone else's
document rather than one the Business issues, so a wrong one is corrected or
removed rather than reversed.
_Avoid_: Purchase invoice, purchase bill, GRN, inward, stock-in

**Received date**:
The day a Purchase's Goods arrived, and the day its Stock movements are dated.
Distinct from the bill date printed by the Supplier, which it usually equals.
_Avoid_: Inward date, GRN date, entry date

**Bill discount**:
A discount a Supplier prints across a whole Purchase rather than on one line.
It lowers the taxable value, and so the tax and the cost, of every line in
proportion to that line's share. A discount given after tax, off what is
payable, is about payment and is not recorded.
_Avoid_: Trade discount, cash discount, overall discount

**Round-off**:
The paise a Supplier adds or takes off to bring a Purchase to a whole rupee,
never more than a rupee either way.
_Avoid_: Adjustment, rounding difference

**Opening stock**:
The quantity and cost of each Item on hand on the day billow starts counting
stock, entered once rather than disguised as a Purchase from nobody.
_Avoid_: Initial stock, stock-take, balance brought forward

**Stock start date**:
The date the Business begins counting stock, recorded by the Business rather
than fixed by billow, and free to change. Stock on hand counts only movements
on or after it; Opening stock is counted as of it. Until it is set, no stock is
counted at all.
_Avoid_: Go-live date, cut-over, inventory start

**Stock movement**:
A recorded change to how much of an Item is on hand: Opening stock, a
Purchase, a sale, a return or a Stock adjustment. Stock on hand is the sum of
an Item's movements and is never entered directly.
_Avoid_: Transaction, stock entry, ledger entry

**Stock adjustment**:
A Stock movement with a stated reason, such as damage, wastage or a recount,
for a change no Purchase, sale or return explains.
_Avoid_: Correction, write-off, stock edit

**Category**:
Where an Item sits in the Business's catalogue, at most two levels deep, such
as Fittings › Elbow. Used to find and filter Items; it decides nothing about
tax or price.
_Avoid_: Group, class, family, department

**Brand**:
The maker an Item is sold under, such as Jaquar or Astral. Used to find and
filter Items.
_Avoid_: Manufacturer, make, company

**Item code**:
The short code every Item carries, assigned by billow unless the Operator gives
one, and the one printed on the Business's own labels. Distinct from a maker's
barcode, which an Item may also answer to when scanned.
_Avoid_: SKU, barcode, product code, part number

**MRP**:
The maximum retail price printed on packaged Goods, which no sale may exceed.
Distinct from the selling price, which is what the Business actually charges
and is usually lower.
_Avoid_: List price, retail price, sticker price

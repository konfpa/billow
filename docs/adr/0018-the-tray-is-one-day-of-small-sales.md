# The Tray holds one day of small Counter sales, and nothing else

A Counter sale below the Tray limit may go in the Tray instead of being
invoiced on its own. The limit defaults to ₹200 and cannot be set higher. The
Tray is billed as one consolidated Invoice dated its own day. If nobody bills
it, the first Invoice issued on a later date bills it first, so numbers and
dates stay in order. A Tray sale moves stock when it is made. It cannot be
edited, only removed with a reason before the Tray is billed.

## Considered Options

A general "sell now, bill later" tray, where a contractor's pickups gather over
a week and are invoiced together, is what Operators ask for, and it is the same
mechanism with the limits taken off. It is not allowed for goods: s.31(1)
requires the invoice at or before the goods are removed. The one exception is
s.31(3)(b) with the proviso to Rule 46. A supply under ₹200 to an unregistered
recipient who does not ask for an invoice may go without one, provided a
consolidated invoice for all such supplies is issued at the close of each day.
The Tray is that exception and no wider. A contractor's running account is a
credit sale, which ADR 0014 defers.

A Customer who has been recorded is never put in the Tray. Recording them is
taken as their asking for an Invoice.

## Consequences

The limit is capped in code rather than trusted to settings, so no
configuration can turn the Tray into a tab. Tray sales are unnumbered records
whose lines become an Invoice later. A Tray sale is not bound by ADR 0015 until
then, which is why removing one is a separate permission and always recorded.

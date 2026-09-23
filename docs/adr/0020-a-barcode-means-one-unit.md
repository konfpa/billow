# A Barcode means one of a unit, not an Item

A Barcode is held against one of an Item's units, never against the Item.
Scanning it adds one of that unit. One unit may answer to several Barcodes.
Every Barcode is unique across all Barcodes and all Item codes, so a scan
resolves to exactly one thing. Opening a box is not recorded: stock is counted
in the stock unit whichever unit was sold (ADR 0011).

## Considered Options

A Barcode on the Item reads as the obvious place, and it is where most
catalogues keep one. It is wrong for anything sold both packed and loose. The
EAN on a box of 100 screws would add one screw, billing ₹0.60 for ₹50 and
moving stock by 1 instead of 100, with nothing on screen to show it. Guessing
the unit from the price, or asking on every scan, would slow the one thing a
scanner is for.

Tracking sealed and opened boxes separately was rejected for the reason ADR
0011 gives: it needs an event nobody records at a counter.

## Consequences

Teaching billow a Barcode always means choosing a unit, and the dialog never
pre-selects one, because a wrong unit is a silent mispricing rather than an
error. A unit that is to answer to a box code must exist on the Item first.

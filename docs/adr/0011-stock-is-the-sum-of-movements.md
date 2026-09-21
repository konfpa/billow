# Stock on hand is the sum of movements, counted in one stock unit

An Item's stock on hand is never stored as an editable figure. It is the sum of
its Stock movements (Opening stock, Purchases, sales, returns and Stock
adjustments), each counted in the Item's stock unit, and it may go negative.
Every other unit is a fixed rate against the stock unit, decimals allowed, so a
pipe bought by the piece and sold by the foot moves one number.

## Considered Options

An editable quantity on the Item is simpler and loses the reason for every
change, which is the first thing an auditor asks for. Refusing a sale that
would take stock below zero protects the number and punishes the wrong party:
the goods are at the counter, so the record is what is wrong, and blocking the
sale pushes it onto a One-off line that moves no stock at all.

Counting in pieces with fractional sales was rejected because 19.8 pipes hides
a cut length on the shelf. Defining conversions between every pair of units was
rejected because pairs can contradict each other; rates against one stock unit
cannot.

## Consequences

Correcting stock always means recording an adjustment with a reason, never
editing a number. Negative stock is expected in the data and is surfaced by a
report rather than prevented. Changing an Item's stock unit after movements
exist means converting every one of them.

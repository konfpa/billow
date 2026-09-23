from django.db import models


class StockMovement(models.Model):
    """A recorded change to how much of an Item is on hand. See CONTEXT.md.

    Stock on hand is the sum of these, never a stored figure; see
    docs/adr/0011-stock-is-the-sum-of-movements.md. A Purchase's Goods lines
    are the only source so far; Opening stock, sales, returns and Stock
    adjustments will be others, which is why the line may be empty.
    """

    item = models.ForeignKey(
        "catalogue.Item", on_delete=models.PROTECT, related_name="stock_movements"
    )
    date = models.DateField()
    # In the Item's stock unit, and negative for stock going out.
    quantity = models.DecimalField(max_digits=18, decimal_places=3)
    cost_per_stock_unit = models.DecimalField(max_digits=14, decimal_places=2)
    purchase_line = models.OneToOneField(
        "purchases.PurchaseLine",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_movement",
    )

    class Meta:
        ordering = ("-date", "-pk")

    def __str__(self) -> str:
        return f"{self.quantity} of {self.item} on {self.date}"

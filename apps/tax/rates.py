from decimal import Decimal

from django.db import models


class GSTRate(Decimal, models.Choices):
    """The GST rate slabs in force since 22 September 2025.

    A fixed set rather than a typed figure, so that a rate the law does not
    have cannot reach a return. When the law changes, this changes in a
    release; an invoice copies the rate onto its line, so an issued invoice is
    untouched by it. Written to two places, as the column stores them, so a
    rate read back from the database matches its choice by spelling too.
    """

    NIL = "0.00", "0%"
    QUARTER = "0.25", "0.25%"
    THREE = "3.00", "3%"
    FIVE = "5.00", "5%"
    EIGHTEEN = "18.00", "18%"
    FORTY = "40.00", "40%"

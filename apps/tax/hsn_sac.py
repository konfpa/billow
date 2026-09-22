"""Validation of the codes that classify an Item: HSN for Goods, SAC for a Service.

Both are stored in one field and read by the Item's kind, so each is judged
here on its own and the Item decides which one applies.
"""

import re

from django.core.exceptions import ValidationError

# Chapter, heading, subheading and tariff item: 4, 6 or 8 digits. How many a
# Business must print is not tied to its turnover here, since a longer code is
# always accepted where a shorter one is asked for.
HSN_SHAPE = re.compile(r"^(?:[0-9]{4}|[0-9]{6}|[0-9]{8})$")

# Services sit in chapter 99 of the same scheme, which is why no HSN code for
# Goods begins with it.
SAC_SHAPE = re.compile(r"^99[0-9]{4}$")


def validate_hsn(code: str) -> None:
    """Refuse anything that is not an HSN code a Goods Item could carry."""
    if SAC_SHAPE.fullmatch(code):
        msg = "That is a SAC, which classifies a Service rather than Goods."
        raise ValidationError(msg, code="hsn_is_sac")

    if not HSN_SHAPE.fullmatch(code) or code.startswith("99"):
        msg = "An HSN code is 4, 6 or 8 digits."
        raise ValidationError(msg, code="hsn_shape")


def validate_sac(code: str) -> None:
    """Refuse anything that is not a SAC a Service Item could carry."""
    if not SAC_SHAPE.fullmatch(code):
        msg = "A SAC is 6 digits beginning 99."
        raise ValidationError(msg, code="sac_shape")


def validate_hsn_or_sac(code: str) -> None:
    """Refuse anything that is neither, for a line that names no Item and so no kind."""
    if SAC_SHAPE.fullmatch(code):
        return
    try:
        validate_hsn(code)
    except ValidationError as error:
        msg = "An HSN code is 4, 6 or 8 digits, and a SAC is 6 digits beginning 99."
        raise ValidationError(msg, code="hsn_sac_shape") from error

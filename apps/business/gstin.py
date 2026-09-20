"""Validation of a GSTIN, India's 15-character GST registration number."""

import re

from django.core.exceptions import ValidationError

from apps.business.states import State

# Two state digits, the holder's ten-character PAN, an entity number for the
# holder's nth registration in that state, a literal Z, and a checksum.
SHAPE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")

# The checksum works in base 36, so every character a GSTIN may carry has a
# value and the alphabet doubles as the digits the check character comes from.
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def state_code_of(gstin: str) -> str:
    """The state code a GSTIN embeds, which is its first two digits."""
    return gstin[:2]


def checksum_of(gstin: str) -> str:
    """The check character the first fourteen of a GSTIN's characters imply."""
    total = 0
    for position, character in enumerate(gstin[:-1]):
        # Every second character counts double, and a product that overflows
        # base 36 is folded back into one digit by adding its two halves.
        product = ALPHABET.index(character) * (2 if position % 2 else 1)
        total += product // len(ALPHABET) + product % len(ALPHABET)

    return ALPHABET[(len(ALPHABET) - total % len(ALPHABET)) % len(ALPHABET)]


def validate_gstin(gstin: str) -> None:
    """Refuse anything that is not a GSTIN some office could have issued.

    Shape, state code and checksum are all checked here, because a GSTIN
    that is wrong is copied onto every invoice issued under it.
    """
    if not SHAPE.fullmatch(gstin):
        msg = "A GSTIN is 15 characters: 22AAAAA0000A1Z5, in capitals."
        raise ValidationError(msg, code="gstin_shape")

    if state_code_of(gstin) not in State.values:
        msg = "That GSTIN starts with a state code no state uses."
        raise ValidationError(msg, code="gstin_state_code")

    if gstin[-1] != checksum_of(gstin):
        msg = "That GSTIN fails its checksum, so a character is wrong."
        raise ValidationError(msg, code="gstin_checksum")

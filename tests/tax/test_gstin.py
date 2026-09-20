import pytest
from django.core.exceptions import ValidationError

from apps.tax.gstin import state_code_of, validate_gstin

# A GSTIN is 2 state digits, the holder's 10-character PAN, an entity number,
# a literal Z and a checksum character. These are real, published numbers:
# invented ones cannot be, because the checksum has to agree.
VALID = [
    "27AAPFU0939F1ZV",
    "29AAGCB7383J1Z4",
    "07AAACS8577K1ZR",
]

REFUSED = [
    ("", "nothing at all"),
    ("27AAPFU0939F1Z", "one character short"),
    ("27AAPFU0939F1ZVV", "one character long"),
    ("27AAPFU0939F1ZW", "a checksum that does not agree"),
    ("27AAPFU0939F1AA", "a Z that is not a Z"),
    ("27AAPFU0939F1ZV ", "a trailing space"),
    ("27aapfu0939f1zv", "lower case"),
    ("00AAPFU0939F1ZB", "a state code no state has"),
    ("AAAAPFU0939F1ZH", "letters where the state code belongs"),
    ("270APFU0939F1Z5", "digits where the PAN belongs"),
]


@pytest.mark.parametrize("gstin", VALID)
def test_a_real_gstin_is_accepted(gstin):
    validate_gstin(gstin)


@pytest.mark.parametrize(("gstin", "fault"), REFUSED)
def test_a_gstin_is_refused(gstin, fault):
    with pytest.raises(ValidationError):
        validate_gstin(gstin)


@pytest.mark.parametrize(
    ("gstin", "state"),
    [("27AAPFU0939F1ZV", "27"), ("29AAGCB7383J1Z4", "29"), ("07AAACS8577K1ZR", "07")],
)
def test_the_state_a_gstin_embeds_is_read_from_its_first_two_digits(gstin, state):
    assert state_code_of(gstin) == state

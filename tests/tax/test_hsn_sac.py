import pytest
from django.core.exceptions import ValidationError

from apps.tax.hsn_sac import validate_hsn, validate_sac

# 7318 is screws and bolts, 848180 taps and valves, 39172390 PVC pipe; 995461
# is installation work and 996511 road transport of goods.
HSN = ["7318", "848180", "39172390"]
SAC = ["995461", "996511"]

REFUSED_AS_HSN = [
    ("", "nothing at all"),
    ("731", "three digits"),
    ("73181", "five digits"),
    ("7318150", "seven digits"),
    ("731815000", "nine digits"),
    ("7318 15", "a space"),
    ("73A8", "a letter"),
    ("995461", "a SAC"),
]

REFUSED_AS_SAC = [
    ("", "nothing at all"),
    ("99546", "five digits"),
    ("9954611", "seven digits"),
    ("848180", "an HSN code of six digits"),
    ("7318", "an HSN code of four digits"),
    ("99546A", "a letter"),
]


@pytest.mark.parametrize("code", HSN)
def test_an_hsn_code_of_4_6_or_8_digits_is_accepted(code):
    validate_hsn(code)


@pytest.mark.parametrize(("code", "fault"), REFUSED_AS_HSN)
def test_an_hsn_code_is_refused(code, fault):
    with pytest.raises(ValidationError):
        validate_hsn(code)


@pytest.mark.parametrize("code", SAC)
def test_a_sac_of_6_digits_beginning_99_is_accepted(code):
    validate_sac(code)


@pytest.mark.parametrize(("code", "fault"), REFUSED_AS_SAC)
def test_a_sac_is_refused(code, fault):
    with pytest.raises(ValidationError):
        validate_sac(code)


def test_a_sac_given_as_an_hsn_code_is_told_why():
    with pytest.raises(ValidationError, match="Service"):
        validate_hsn("995461")

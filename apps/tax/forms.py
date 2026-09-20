from django import forms


class TaxCodeField(forms.CharField):
    """A GSTIN, PAN or CIN, folded to capitals before anything checks it.

    The codes are issued in capitals and stored as issued, so a lower-case
    entry is a keyboard state rather than a different number.
    """

    def to_python(self, value: object) -> str:
        return (super().to_python(value) or "").upper()

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

# Beyond these an address pushes the invoice header out of shape.
MAX_LINES = 5
MAX_CHARACTERS = 500


def validate_address_lines(address: str) -> None:
    if len(address.splitlines()) > MAX_LINES:
        msg = f"An address fits on {MAX_LINES} lines or fewer."
        raise ValidationError(msg)


def validate_address_length(address: str) -> None:
    if len(address) > MAX_CHARACTERS:
        msg = f"An address is {MAX_CHARACTERS} characters or fewer."
        raise ValidationError(msg)


class AddressField(models.TextField):
    """The street part of an address, one line per line it prints on.

    City, PIN code and state stay separate fields beside it, because the place
    of supply and the GSTIN's state are read from them.
    """

    default_validators = [validate_address_lines, validate_address_length]

    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault(
            "help_text", "Building, street and area, one per line, as it should print."
        )
        super().__init__(*args, **kwargs)

    def to_python(self, value: object) -> str | None:
        # Normalised here rather than in a form, so that the admin, a form and
        # the shell store the same thing, and the limits are judged against
        # what will be stored rather than against what was typed.
        value = super().to_python(value)
        if value is None:
            return value

        lines = (line.strip() for line in value.splitlines())
        return "\n".join(line for line in lines if line)

    def formfield(self, **kwargs: object) -> forms.Field:
        return super().formfield(
            **{"widget": forms.Textarea(attrs={"rows": 3}), **kwargs}
        )

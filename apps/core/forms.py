from typing import TYPE_CHECKING

from django import forms

if TYPE_CHECKING:
    from django.core.exceptions import ValidationError


class StyledForm(forms.ModelForm):
    """A ModelForm whose inputs are dressed the way billow's pages expect.

    Done here rather than in the template, which cannot add a class to an
    already-rendered widget, and per form rather than per field so that a
    field added to a form is styled by having been added at all.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            # A radio group and a file picker are not text boxes, and the
            # `field` utility styles a text box.
            if not isinstance(field.widget, forms.RadioSelect | forms.FileInput):
                field.widget.attrs.setdefault("class", "field")

    def add_error(self, field: str | None, error: ValidationError | str) -> None:
        super().add_error(field, error)

        # Every error billow raises — the field's, the model's, this form's —
        # arrives through add_error, so one hook marks all of them.
        if field in self.fields:
            attrs = self.fields[field].widget.attrs
            if "field" in attrs.get("class", "").split():
                attrs["class"] += " field-invalid"

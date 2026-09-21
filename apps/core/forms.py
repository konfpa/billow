from django import forms

# konspec field/django, select/django and textarea/django. The widget renders
# the control alone: the bordered wrapper, the focus outline and the error
# border are drawn by templates/forms/field.html around it.
CONTROL = "w-full bg-transparent px-3 py-2 text-[14px]/5 tabular-nums outline-none"
SELECT = (
    "block w-full min-w-0 appearance-none bg-transparent py-2 pr-9 pl-3 "
    "text-[14px]/5 outline-none"
)
TEXTAREA = (
    "block w-full bg-transparent px-3 py-2 text-[14px]/5 outline-none "
    "placeholder:text-zinc-500"
)


class StyledForm(forms.ModelForm):
    """A ModelForm whose controls are dressed and wired the way konspec asks.

    Done here rather than in the template, which cannot add an attribute to an
    already-rendered widget, and per form rather than per field so that a
    field added to a form is styled by having been added at all.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # A radio group and a file picker are drawn by hand on the page,
            # with no field wrapper and no message line to describe them by.
            if isinstance(field.widget, forms.RadioSelect | forms.FileInput):
                continue

            attrs = field.widget.attrs
            if isinstance(field.widget, forms.Select):
                attrs.setdefault("class", SELECT)
            elif isinstance(field.widget, forms.Textarea):
                attrs.setdefault("class", TEXTAREA)
            else:
                attrs.setdefault("class", CONTROL)
            attrs["aria-describedby"] = f"{self[name].auto_id}-msg"
            attrs["aria-invalid"] = "false"

    def full_clean(self) -> None:
        super().full_clean()

        # Decided once validation has run, from every error it produced — the
        # field's, the model's, this form's — rather than hooked into
        # add_error, which a ModelForm bypasses for a model's error dict.
        for name, field in self.fields.items():
            if "aria-invalid" in field.widget.attrs:
                field.widget.attrs["aria-invalid"] = (
                    "true" if name in self.errors else "false"
                )

    @property
    def invalid_fields(self) -> list[forms.BoundField]:
        """The fields that failed, in form order, for the error summary."""
        return [field for field in self if field.errors]

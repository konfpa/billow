from django import forms

from apps.business.models import Business


class TaxCodeField(forms.CharField):
    """A GSTIN, PAN or CIN, folded to capitals before anything checks it.

    The codes are issued in capitals and stored as issued, so a lower-case
    entry is a keyboard state rather than a different number.
    """

    def to_python(self, value: object) -> str:
        return (super().to_python(value) or "").upper()


class BusinessForm(forms.ModelForm):
    # Declared rather than inferred from the nullable column: Django's
    # NullBooleanField offers "Unknown" as a third answer, and unanswered is
    # exactly what this field exists to rule out.
    is_gst_registered = forms.TypedChoiceField(
        label="GST registered",
        choices=[("True", "Yes, the Business holds a GSTIN"), ("False", "No")],
        coerce=lambda value: value == "True",
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Business
        fields = (
            "name",
            "legal_name",
            "address_line_1",
            "address_line_2",
            "city",
            "postal_code",
            "state",
            "is_gst_registered",
            "gstin",
            "pan",
            "cin",
            "email",
            "phone",
            "website",
            "logo",
        )
        field_classes = {
            "gstin": TaxCodeField,
            "pan": TaxCodeField,
            "cin": TaxCodeField,
        }
        labels = {
            "name": "Name",
            "legal_name": "Legal name",
            "address_line_1": "Address",
            "address_line_2": "Address, continued",
        }
        help_texts = {
            "legal_name": (
                "Leave blank if the Business trades under its registered name."
            ),
        }
        widgets = {
            "state": forms.Select(attrs={"class": "field"}),
            "logo": forms.ClearableFileInput(
                attrs={"class": "text-note", "accept": "image/*"}
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # One list decides what setup demands, so a release that adds a
            # requirement changes the model and this form follows.
            field.required = name in Business.REQUIRED_FOR_SETUP

            # A radio group and a file picker are not text boxes, and the
            # `field` utility styles a text box.
            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "mt-0.5 h-4 w-4 accent-accent")
            elif not isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault("class", "field")

        self.fields["state"].empty_label = "Choose a state"

    def add_error(self, field: str | None, error: object) -> None:
        super().add_error(field, error)

        # Marking the input itself is done here rather than in the template,
        # which cannot add a class to an already-rendered widget. Every error
        # billow raises — the field's, the model's, this form's — arrives
        # through add_error, so one hook covers all of them.
        if field in self.fields:
            attrs = self.fields[field].widget.attrs
            if "field" in attrs.get("class", "").split():
                attrs["class"] += " field-invalid"

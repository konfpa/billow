from django import forms

from apps.business.models import Business
from apps.core.forms import StyledForm
from apps.tax.forms import TaxCodeField


class LogoInput(forms.ClearableFileInput):
    """A file input with no chrome of its own.

    Django's clearable input renders "Currently / Change / Clear" around the
    input; the page draws all of that itself. The class stays a
    ClearableFileInput so the clear checkbox the page renders is still read
    back off the POST.
    """

    template_name = "django/forms/widgets/file.html"

    def format_value(self, value: object) -> None:  # noqa: ARG002
        # The clearable widget hands the stored name back as the input's
        # value, which a file input has no use for: the page shows what is on
        # file itself, and browsers ignore the attribute anyway.
        return None


class BusinessForm(StyledForm):
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
            "logo": LogoInput(
                attrs={
                    "class": "sr-only",
                    "accept": "image/png,image/jpeg,image/webp,image/svg+xml",
                    "x-ref": "input",
                    "x-on:change": "chosen",
                }
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # One list decides what setup demands, so a release that adds a
            # requirement changes the model and this form follows.
            field.required = name in Business.REQUIRED_FOR_SETUP

            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "mt-0.5 h-4 w-4 accent-accent")

        self.fields["state"].empty_label = "Choose a state"

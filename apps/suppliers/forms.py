from apps.core.forms import StyledForm
from apps.suppliers.models import Supplier
from apps.tax.forms import TaxCodeField
from apps.tax.states import State


class SupplierForm(StyledForm):
    class Meta:
        model = Supplier
        fields = (
            "name",
            "legal_name",
            "address",
            "city",
            "postal_code",
            "state",
            "gstin",
            "email",
            "phone",
        )
        field_classes = {"gstin": TaxCodeField}
        labels = {
            "name": "Name",
            "legal_name": "Legal name",
        }
        help_texts = {
            "legal_name": (
                "Leave blank if the Supplier trades under its registered name."
            ),
            "gstin": "Leave blank for a Supplier who holds no registration.",
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # One list decides what a Supplier must answer, so a release that
            # adds a requirement changes the model and this form follows.
            field.required = name in Supplier.REQUIRED_TO_RECORD

        # A ModelForm's choice field takes no empty_label, so the prompt
        # replaces the blank choice Django puts in front of the states.
        self.fields["state"].choices = [("", "Choose a state"), *State.choices]

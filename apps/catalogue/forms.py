from django import forms
from django.db import transaction

from apps.catalogue.models import Item, ItemUnit
from apps.core.forms import StyledForm
from apps.tax.rates import GSTRate
from apps.tax.units import UQC


class ItemForm(StyledForm):
    """An Item and its stock unit, recorded together."""

    stock_unit = forms.ChoiceField(
        choices=[("", "Choose a unit"), *UQC.choices],
        help_text="The unit the Item is sold in, and its stock counted in.",
    )
    selling_price = forms.DecimalField(
        label="Selling price",
        max_digits=12,
        decimal_places=2,
        min_value=0,
        help_text="Per stock unit, including GST.",
    )

    class Meta:
        model = Item
        fields = ("name", "kind", "hsn_sac", "gst_rate")
        labels = {"name": "Name"}

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # One list decides what an Item must answer, so a release that
            # adds a requirement changes the model and this form follows.
            field.required = name in Item.REQUIRED_TO_RECORD

        # A ModelForm's choice field takes no empty_label, so the prompt
        # replaces the blank choice Django puts in front of the choices.
        self.fields["kind"].choices = [
            ("", "Choose Goods or Service"),
            *Item.Kind.choices,
        ]
        self.fields["gst_rate"].choices = [("", "Choose a rate"), *GSTRate.choices]

    @transaction.atomic
    def save(self) -> Item:
        item = super().save()
        ItemUnit.objects.create(
            item=item,
            uqc=self.cleaned_data["stock_unit"],
            is_stock_unit=True,
            selling_price=self.cleaned_data["selling_price"],
        )
        return item

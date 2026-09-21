from django import forms
from django.db import transaction

from apps.catalogue.models import Item, ItemUnit
from apps.core.forms import StyledForm
from apps.tax.rates import GSTRate
from apps.tax.units import UQC


class ItemCodeField(forms.CharField):
    """An Item code, folded to capitals before anything checks it.

    A lower-case entry is a keyboard state rather than a different code, and
    both must find the same Item when a label is scanned. Only plain letters
    are folded, since some others capitalise into them, as ß does into SS.
    """

    def to_python(self, value: object) -> str:
        code = super().to_python(value) or ""
        return code.upper() if code.isascii() else code


class ItemForm(StyledForm):
    """An Item and its stock unit, recorded and edited together."""

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
        fields = ("name", "kind", "code", "hsn_sac", "gst_rate")
        field_classes = {"code": ItemCodeField}
        labels = {"name": "Name"}
        help_texts = {"code": "Leave blank for billow to assign the next one."}

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

        if unit := self.instance.stock_unit if self.instance.pk else None:
            self.initial.setdefault("stock_unit", unit.uqc)
            self.initial.setdefault("selling_price", unit.selling_price)

        if self.instance.pk:
            self.fields["code"].help_text = "Leave blank to keep the code on file."

    def clean_code(self) -> str:
        return self.cleaned_data["code"] or self.instance.code

    @transaction.atomic
    def save(self) -> Item:
        item = super().save()
        unit = item.stock_unit or ItemUnit(item=item, is_stock_unit=True)

        # Saved only when changed, so the unit's history holds real changes.
        if unit.pk and not {"stock_unit", "selling_price"} & set(self.changed_data):
            return item

        # The stock unit changes freely while no stock movements exist; see
        # docs/adr/0011-stock-is-the-sum-of-movements.md.
        unit.uqc = self.cleaned_data["stock_unit"]
        unit.selling_price = self.cleaned_data["selling_price"]
        unit.save()
        return item

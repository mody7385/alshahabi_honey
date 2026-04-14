from django import forms

from .models import Product


class ManagerProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'warehouse',
            'name',
            'honey_type',
            'purchase_price_per_kg',
            'default_sale_price_per_dabba',
            'default_sale_price_per_kg',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
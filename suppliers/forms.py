from django import forms
from django.db import models

from .models import Supplier, SupplierPayment, SupplierPurchase


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'address', 'notes', 'is_active']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class SupplierPurchaseForm(forms.ModelForm):
    class Meta:
        model = SupplierPurchase
        fields = [
            'supplier',
            'product',
            'quantity_dabba',
            'quantity_kg',
            'price_per_dabba',
            'price_per_kg',
            'add_to_inventory',
            'purchase_date',
            'notes',
        ]
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['quantity_dabba'].widget.attrs['step'] = '0.5'
        self.fields['add_to_inventory'].widget.attrs['class'] = ''
        product_queryset = self.fields['product'].queryset.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.product_id:
            product_queryset = self.fields['product'].queryset.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.product_id)
            )
        self.fields['product'].queryset = product_queryset


class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = ['supplier', 'amount', 'payment_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

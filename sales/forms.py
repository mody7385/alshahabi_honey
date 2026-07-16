from django import forms

from .models import Sale, SaleBatch


class SaleHeaderForm(forms.ModelForm):
    customer_name = forms.CharField(required=False, label='اسم العميل')
    customer_phone = forms.CharField(required=False, label='رقم جوال العميل')

    class Meta:
        model = SaleBatch
        fields = ['payment_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        customer_name = cleaned_data.get('customer_name')
        customer_phone = cleaned_data.get('customer_phone')

        if payment_type == 'deferred' and not customer_name and not customer_phone:
            raise forms.ValidationError('في البيع الآجل يجب إدخال اسم العميل أو رقم الجوال.')

        return cleaned_data


class SaleLineForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'product',
            'quantity_dabba',
            'price_per_dabba',
            'quantity_kg',
            'price_per_kg',
        ]

    def __init__(self, *args, **kwargs):
        worker_profile = kwargs.pop('worker_profile', None)
        super().__init__(*args, **kwargs)

        if worker_profile and worker_profile.warehouse:
            self.fields['product'].queryset = self.fields['product'].queryset.filter(
                warehouse=worker_profile.warehouse,
                is_active=True,
            )

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['quantity_dabba'].widget.attrs['step'] = '0.5'
        self.fields['quantity_kg'].widget.attrs['step'] = '0.01'

    def is_empty(self):
        data = self.cleaned_data if hasattr(self, 'cleaned_data') else {}
        return not data.get('product') and not data.get('quantity_dabba') and not data.get('quantity_kg')

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data or self.is_empty():
            return cleaned_data

        quantity_dabba = cleaned_data.get('quantity_dabba') or 0
        quantity_kg = cleaned_data.get('quantity_kg') or 0
        price_per_dabba = cleaned_data.get('price_per_dabba') or 0
        price_per_kg = cleaned_data.get('price_per_kg') or 0

        if not cleaned_data.get('product'):
            raise forms.ValidationError('اختر المنتج.')

        if quantity_dabba == 0 and quantity_kg == 0:
            raise forms.ValidationError('أدخل كمية مباعة.')

        if quantity_dabba > 0 and price_per_dabba <= 0:
            raise forms.ValidationError('أدخل سعر الدبة.')

        if quantity_kg > 0 and price_per_kg <= 0:
            raise forms.ValidationError('أدخل سعر الكيلو.')

        return cleaned_data


class WorkerSaleForm(SaleLineForm):
    customer_name = forms.CharField(required=False, label='اسم العميل')
    customer_phone = forms.CharField(required=False, label='رقم جوال العميل')

    class Meta(SaleLineForm.Meta):
        fields = SaleLineForm.Meta.fields + ['payment_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.customer:
            self.fields['customer_name'].initial = self.instance.customer.name
            self.fields['customer_phone'].initial = self.instance.customer.phone

        self.fields['customer_name'].widget.attrs['class'] = 'form-control'
        self.fields['customer_phone'].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        customer_name = cleaned_data.get('customer_name')
        customer_phone = cleaned_data.get('customer_phone')

        if payment_type == 'deferred' and not customer_name and not customer_phone:
            raise forms.ValidationError('في البيع الآجل يجب إدخال اسم العميل أو رقم الجوال.')

        return cleaned_data

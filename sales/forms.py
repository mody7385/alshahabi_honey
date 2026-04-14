from django import forms

from .models import Sale


class WorkerSaleForm(forms.ModelForm):
    customer_name = forms.CharField(
        required=False,
        label='اسم العميل',
    )
    customer_phone = forms.CharField(
        required=False,
        label='رقم جوال العميل',
    )

    class Meta:
        model = Sale
        fields = [
            'product',
            'quantity_dabba',
            'price_per_dabba',
            'quantity_kg',
            'price_per_kg',
            'payment_type',
            'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        worker_profile = kwargs.pop('worker_profile', None)
        super().__init__(*args, **kwargs)

        if worker_profile and worker_profile.warehouse:
            self.fields['product'].queryset = self.fields['product'].queryset.filter(
                warehouse=worker_profile.warehouse,
                is_active=True
            )

        if self.instance and self.instance.pk and self.instance.customer:
            self.fields['customer_name'].initial = self.instance.customer.name
            self.fields['customer_phone'].initial = self.instance.customer.phone

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

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
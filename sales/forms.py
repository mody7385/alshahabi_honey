from django import forms

from accounting.models import FinancialAccount
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
        else:
            self.fields['product'].queryset = self.fields['product'].queryset.filter(is_active=True)

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
        fields = SaleLineForm.Meta.fields + ['payment_type', 'cash_worker_account', 'payment_account', 'notes']
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
        self.fields['cash_worker_account'].queryset = FinancialAccount.objects.filter(
            account_type='worker',
            is_active=True,
        )
        self.fields['payment_account'].queryset = FinancialAccount.objects.filter(
            account_type__in=['cashbox', 'bank', 'wallet'],
            is_active=True,
        )

        if not (self.instance and self.instance.pk and self.instance.is_new_accounting_sale):
            self.fields.pop('cash_worker_account', None)
            self.fields.pop('payment_account', None)

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        customer_name = cleaned_data.get('customer_name')
        customer_phone = cleaned_data.get('customer_phone')

        if payment_type == 'deferred' and not customer_name and not customer_phone:
            raise forms.ValidationError('في البيع الآجل يجب إدخال اسم العميل أو رقم الجوال.')

        return cleaned_data


class ManagerSaleHeaderForm(forms.Form):
    store = forms.ChoiceField(
        choices=SaleBatch.STORE_CHOICES,
        required=False,
        initial=SaleBatch.STORE_ALSHAHABI,
        label='المتجر',
    )
    customer_name = forms.CharField(required=False, label='اسم العميل')
    customer_phone = forms.CharField(required=False, label='رقم جوال العميل')
    payment_type = forms.ChoiceField(
        choices=SaleBatch.PAYMENT_CHOICES,
        required=False,
        label='نوع الدفع',
        widget=forms.HiddenInput,
    )
    cash_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        initial=0,
        label='مبلغ النقد',
    )
    transfer_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        initial=0,
        label='مبلغ الحوالة',
    )
    deferred_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        initial=0,
        label='مبلغ الآجل',
    )
    cash_worker_account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.none(),
        required=False,
        label='حساب العامل',
    )
    payment_account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.none(),
        required=False,
        label='الحساب المالي',
    )
    notes = forms.CharField(
        required=False,
        label='ملاحظات',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cash_worker_account'].queryset = FinancialAccount.objects.filter(
            account_type='worker',
            is_active=True,
        ).order_by('name')
        self.fields['payment_account'].queryset = FinancialAccount.objects.filter(
            account_type__in=['cashbox', 'bank', 'wallet'],
            is_active=True,
        ).order_by('account_type', 'name')

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        customer_name = cleaned_data.get('customer_name')
        customer_phone = cleaned_data.get('customer_phone')
        cash_amount = cleaned_data.get('cash_amount') or 0
        transfer_amount = cleaned_data.get('transfer_amount') or 0
        deferred_amount = cleaned_data.get('deferred_amount') or 0

        if cash_amount > 0 and not cleaned_data.get('cash_worker_account'):
            raise forms.ValidationError('في البيع النقدي يجب اختيار حساب العامل.')

        if transfer_amount > 0 and not cleaned_data.get('payment_account'):
            raise forms.ValidationError('في بيع الحوالة يجب اختيار الحساب المالي.')

        if deferred_amount > 0 and not customer_name and not customer_phone:
            raise forms.ValidationError('في البيع الآجل يجب إدخال اسم العميل أو رقم الجوال.')

        return cleaned_data

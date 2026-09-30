from django import forms

from .models import FinancialAccount


class FinancialAccountForm(forms.ModelForm):
    class Meta:
        model = FinancialAccount
        fields = ['name', 'account_type', 'opening_balance', 'is_active', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ManualAdjustmentForm(forms.Form):
    DIRECTION_CHOICES = [
        ('in', 'إضافة مال'),
        ('out', 'سحب مال'),
    ]
    CATEGORY_CHOICES = [
        ('manual_deposit', 'إضافة مال'),
        ('manual_withdrawal', 'سحب مال'),
        ('personal_expense', 'مصروف شخصي'),
        ('operating_expense', 'مصروف تشغيل'),
    ]

    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True),
        label='الحساب المالي',
    )
    direction = forms.ChoiceField(choices=DIRECTION_CHOICES, label='نوع الحركة')
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, label='المبلغ')
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, label='التصنيف')
    description = forms.CharField(max_length=250, label='الوصف')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = FinancialAccount.objects.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

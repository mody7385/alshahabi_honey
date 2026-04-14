from django import forms


class ManagerInventoryAdjustForm(forms.Form):
    OPERATION_CHOICES = [
        ('add', 'إضافة للمخزون'),
        ('subtract', 'خصم من المخزون'),
        ('set', 'ضبط مباشر للكمية'),
    ]

    operation_type = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        label='نوع العملية'
    )

    quantity_dabba = forms.IntegerField(
        min_value=0,
        initial=0,
        label='عدد الدبب'
    )

    quantity_kg = forms.DecimalField(
        min_value=0,
        max_digits=8,
        decimal_places=2,
        initial=0,
        label='عدد الكيلوات'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        quantity_dabba = cleaned_data.get('quantity_dabba') or 0
        quantity_kg = cleaned_data.get('quantity_kg') or 0

        if quantity_dabba == 0 and quantity_kg == 0:
            raise forms.ValidationError('يجب إدخال كمية أكبر من صفر.')

        return cleaned_data
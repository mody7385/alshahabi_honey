from django import forms

from .models import OperatingExpense, WorkerAccountTransaction


class ManagerWorkerTransactionForm(forms.ModelForm):
    class Meta:
        model = WorkerAccountTransaction
        fields = [
            'transaction_type',
            'amount',
            'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_types = ['expense', 'addition', 'deduction']
        self.fields['transaction_type'].choices = [
            choice for choice in self.fields['transaction_type'].choices
            if choice[0] in allowed_types
        ]

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ManagerOperatingExpenseForm(forms.ModelForm):
    class Meta:
        model = OperatingExpense
        fields = [
            'name',
            'category',
            'amount',
            'expense_date',
            'notes',
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
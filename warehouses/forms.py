from django import forms

from .models import Warehouse


class ManagerWarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            'name',
            'city',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
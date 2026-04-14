from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from .models import WorkerProfile


class ManagerUserForm(forms.ModelForm):
    username = forms.CharField(label='اسم المستخدم')
    password = forms.CharField(
        label='كلمة المرور',
        required=False,
        widget=forms.PasswordInput
    )

    class Meta:
        model = WorkerProfile
        fields = [
            'full_name',
            'phone',
            'role',
            'warehouse',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.user:
            self.fields['username'].initial = self.instance.user.username

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['password'].widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username)

        if self.instance and self.instance.pk and self.instance.user:
            qs = qs.exclude(pk=self.instance.user.pk)

        if qs.exists():
            raise forms.ValidationError('اسم المستخدم مستخدم من قبل.')

        return username

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        warehouse = cleaned_data.get('warehouse')
        password = cleaned_data.get('password')

        if role == 'worker' and not warehouse:
            raise forms.ValidationError('يجب ربط العامل بمخزن.')

        if not self.instance.pk and not password:
            raise forms.ValidationError('يجب إدخال كلمة المرور عند إنشاء حساب جديد.')

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        username = self.cleaned_data['username']
        password = self.cleaned_data.get('password')

        if self.instance.pk and self.instance.user:
            user = self.instance.user
            user.username = username
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User(username=username)
            user.set_password(password)
            user.save()
            self.instance.user = user

        profile = super().save(commit=commit)
        return profile
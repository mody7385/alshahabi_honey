from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=150, verbose_name='اسم العميل')
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='رقم الجوال')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'عميل'
        verbose_name_plural = 'العملاء'

    def __str__(self):
        return self.name
        
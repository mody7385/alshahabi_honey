from django.db import models


class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم المخزن')
    city = models.CharField(max_length=100, verbose_name='المدينة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'مخزن'
        verbose_name_plural = 'المخازن'

    def __str__(self):
        return self.name
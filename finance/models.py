from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from accounts.models import WorkerProfile


class WorkerAccountTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale_cash', 'بيع نقدي'),
        ('expense', 'مصروف'),
        ('addition', 'إضافة'),
        ('deduction', 'خصم'),
        ('adjustment', 'تسوية'),
    ]

    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        verbose_name='العامل'
    )

    sale = models.OneToOneField(
        'sales.Sale',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='cash_transaction',
        verbose_name='عملية البيع'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع الحركة'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='المبلغ'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'حركة حساب عامل'
        verbose_name_plural = 'حركات حسابات العمال'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker.full_name} - {self.get_transaction_type_display()} - {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('المبلغ يجب أن يكون أكبر من صفر.')

        if self.transaction_type == 'sale_cash' and not self.sale:
            raise ValidationError('البيع النقدي يجب أن يكون مرتبطًا بعملية بيع.')

        if self.transaction_type != 'sale_cash' and self.sale:
            raise ValidationError('ربط عملية بيع مسموح فقط مع نوع "بيع نقدي".')
            from django.utils import timezone


class OperatingExpense(models.Model):
    CATEGORY_CHOICES = [
        ('rent', 'إيجار'),
        ('wages', 'أجور ورواتب'),
        ('transport', 'نقل'),
        ('maintenance', 'صيانة'),
        ('electricity', 'كهرباء'),
        ('other', 'أخرى'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name='اسم المصروف'
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name='التصنيف'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='المبلغ'
    )

    expense_date = models.DateField(
        default=timezone.localdate,
        verbose_name='تاريخ المصروف'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'مصروف تشغيلي'
        verbose_name_plural = 'المصاريف التشغيلية'
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.amount}"
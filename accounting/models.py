from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone


MONEY_ZERO = Decimal('0.00')


class FinancialAccount(models.Model):
    ACCOUNT_TYPES = [
        ('cashbox', 'صندوق'),
        ('bank', 'بنك'),
        ('wallet', 'محفظة'),
        ('worker', 'عامل'),
    ]

    name = models.CharField(max_length=150, verbose_name='اسم الحساب')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name='نوع الحساب')
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='الرصيد الافتتاحي',
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حساب مالي'
        verbose_name_plural = 'الحسابات المالية'
        ordering = ['account_type', 'name']

    def __str__(self):
        return f'{self.name} - {self.get_account_type_display()}'

    def current_balance(self):
        incoming = self.ledger_entries.filter(
            direction='in',
            is_reversed=False,
        ).aggregate(total=Sum('amount')).get('total') or MONEY_ZERO
        outgoing = self.ledger_entries.filter(
            direction='out',
            is_reversed=False,
        ).aggregate(total=Sum('amount')).get('total') or MONEY_ZERO
        return (Decimal(self.opening_balance) + incoming - outgoing).quantize(Decimal('0.01'))


class LedgerEntry(models.Model):
    DIRECTIONS = [
        ('in', 'داخل'),
        ('out', 'خارج'),
    ]

    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        verbose_name='الحساب المالي',
    )
    direction = models.CharField(max_length=3, choices=DIRECTIONS, verbose_name='الاتجاه')
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='المبلغ')
    category = models.CharField(max_length=50, verbose_name='التصنيف')
    description = models.CharField(max_length=250, verbose_name='الوصف')
    source_type = models.CharField(max_length=80, verbose_name='نوع المصدر')
    source_id = models.PositiveIntegerField(verbose_name='رقم المصدر')
    is_reversed = models.BooleanField(default=False, verbose_name='معكوس')
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الحركة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حركة مالية'
        verbose_name_plural = 'دفتر الحركات'
        ordering = ['-occurred_at', '-created_at']
        indexes = [
            models.Index(fields=['source_type', 'source_id', 'is_reversed']),
            models.Index(fields=['account', 'is_reversed']),
        ]

    def __str__(self):
        return f'{self.account.name} - {self.direction} - {self.amount}'

    def clean(self):
        if self.direction not in {'in', 'out'}:
            raise ValidationError('اتجاه الحركة غير صحيح.')
        if self.amount <= 0:
            raise ValidationError('مبلغ الحركة يجب أن يكون أكبر من صفر.')


class MoneyTransfer(models.Model):
    source_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name='من حساب',
    )
    target_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name='إلى حساب',
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='مبلغ التحويل')
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='عمولة التحويل')
    description = models.CharField(max_length=250, verbose_name='الوصف')
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ التحويل')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تحويل مالي'
        verbose_name_plural = 'التحويلات المالية'
        ordering = ['-occurred_at', '-created_at']

    def __str__(self):
        return f'{self.source_account.name} إلى {self.target_account.name} - {self.amount}'

    def clean(self):
        if self.source_account_id and self.target_account_id and self.source_account_id == self.target_account_id:
            raise ValidationError('لا يمكن التحويل بين نفس الحساب.')
        if self.amount <= 0:
            raise ValidationError('مبلغ التحويل يجب أن يكون أكبر من صفر.')
        if self.fee_amount < 0:
            raise ValidationError('عمولة التحويل لا يمكن أن تكون بالسالب.')

    def save(self, *args, **kwargs):
        from .services import post_transfer

        self.full_clean()
        super().save(*args, **kwargs)
        post_transfer(self)

    def delete(self, *args, **kwargs):
        from .services import reverse_entries

        reverse_entries('money_transfer', self.pk)
        super().delete(*args, **kwargs)

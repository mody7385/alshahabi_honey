from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum

from warehouses.models import Warehouse


class WorkerProfile(models.Model):
    ROLE_MANAGER = 'manager'
    ROLE_WORKER = 'worker'

    ROLE_CHOICES = [
        (ROLE_MANAGER, 'مدير'),
        (ROLE_WORKER, 'عامل'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستخدم',
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name='الاسم الكامل',
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='رقم الجوال',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_WORKER,
        verbose_name='الدور',
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='المخزن',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء',
    )

    class Meta:
        verbose_name = 'ملف مستخدم'
        verbose_name_plural = 'ملفات المستخدمين'

    def __str__(self):
        return f'{self.full_name} - {self.get_role_display()}'

    def _sum_transactions(self, transaction_type):
        total = (
            self.workeraccounttransaction_set
            .filter(transaction_type=transaction_type)
            .aggregate(total=Sum('amount'))
            .get('total')
        )
        return total or Decimal('0.00')

    def total_cash_sales(self):
        return self._sum_transactions('sale_cash')

    def total_expenses(self):
        return self._sum_transactions('expense')

    def total_additions(self):
        return self._sum_transactions('addition')

    def total_deductions(self):
        return self._sum_transactions('deduction')

    def final_balance(self):
        return (
            self.total_cash_sales()
            + self.total_additions()
            - self.total_expenses()
            - self.total_deductions()
        )

    def balance_status(self):
        balance = self.final_balance()

        if balance > 0:
            return f'عليه {balance}'
        if balance < 0:
            return f'له {abs(balance)}'
        return 'متوازن'
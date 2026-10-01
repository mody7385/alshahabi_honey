from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import WorkerProfile
from accounting.models import FinancialAccount
from customers.models import Customer
from inventory.models import Inventory
from products.models import Product
from warehouses.models import Warehouse


DABBA_KG = Decimal('6.5')
MONEY_STEP = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


class SaleBatch(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقد'),
        ('transfer', 'حوالة'),
        ('deferred', 'آجل'),
        ('mixed', 'مختلط'),
    ]
    STORE_ALSHAHABI = 'alshahabi'
    STORE_SAMRA = 'samra'
    STORE_CHOICES = [
        (STORE_ALSHAHABI, 'الشهابي'),
        (STORE_SAMRA, 'سمرة'),
    ]

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.PROTECT, verbose_name='العامل')
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='العميل',
    )
    store = models.CharField(
        max_length=20,
        choices=STORE_CHOICES,
        default=STORE_ALSHAHABI,
        verbose_name='المتجر',
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name='نوع الدفع')
    uses_batch_accounting = models.BooleanField(default=False, verbose_name='محاسبة على العملية كاملة')
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبلغ النقد')
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبلغ الحوالة')
    deferred_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='مبلغ الآجل')
    cash_worker_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        limit_choices_to={'account_type': 'worker', 'is_active': True},
        related_name='batch_cash_sales',
        verbose_name='حساب النقد',
    )
    payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        limit_choices_to={'account_type__in': ['cashbox', 'bank', 'wallet'], 'is_active': True},
        related_name='batch_transfer_sales',
        verbose_name='حساب الحوالة',
    )
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ البيع')

    class Meta:
        verbose_name = 'عملية بيع'
        verbose_name_plural = 'عمليات البيع'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker.full_name} - {self.get_payment_type_display()} - {self.created_at:%Y-%m-%d}"

    def total_amount(self):
        return sum((sale.total_amount for sale in self.sales.all()), Decimal('0'))

    def total_profit(self):
        return sum((sale.profit_amount for sale in self.sales.all()), Decimal('0'))

    def total_paid(self):
        return money(Decimal(self.cash_amount) + Decimal(self.transfer_amount) + Decimal(self.deferred_amount))

    def clean_accounting_fields(self, total_amount):
        if self.cash_amount < 0 or self.transfer_amount < 0 or self.deferred_amount < 0:
            raise ValidationError('مبالغ الدفع لا يمكن أن تكون بالسالب.')

        if self.total_paid() != money(total_amount):
            raise ValidationError('مبالغ الدفع يجب أن تساوي إجمالي البيع.')

        if self.cash_amount > 0:
            if not self.cash_worker_account_id:
                raise ValidationError('عند وجود مبلغ نقد يجب اختيار حساب النقد.')
            if self.cash_worker_account.account_type != 'worker':
                raise ValidationError('حساب النقد يجب أن يكون من نوع عامل.')

        if self.transfer_amount > 0:
            if not self.payment_account_id:
                raise ValidationError('عند وجود مبلغ حوالة يجب اختيار الحساب المالي.')
            if self.payment_account.account_type not in {'cashbox', 'bank', 'wallet'}:
                raise ValidationError('حساب الحوالة يجب أن يكون صندوقًا أو بنكًا أو محفظة.')

        if self.deferred_amount > 0 and not self.customer_id:
            raise ValidationError('عند وجود مبلغ آجل يجب إدخال العميل.')

    def derive_payment_type(self):
        parts = sum(1 for amount in [self.cash_amount, self.transfer_amount, self.deferred_amount] if amount > 0)
        if parts > 1:
            return 'mixed'
        if self.transfer_amount > 0:
            return 'transfer'
        if self.deferred_amount > 0:
            return 'deferred'
        return 'cash'


class Sale(models.Model):
    PAYMENT_CHOICES = SaleBatch.PAYMENT_CHOICES

    batch = models.ForeignKey(
        SaleBatch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='sales',
        verbose_name='عملية البيع',
    )

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.PROTECT, verbose_name='العامل')
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='العميل',
    )
    store = models.CharField(
        max_length=20,
        choices=SaleBatch.STORE_CHOICES,
        default=SaleBatch.STORE_ALSHAHABI,
        verbose_name='المتجر',
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='المنتج')

    quantity_dabba = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='عدد الدبب',
    )
    price_per_dabba = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر الدبة',
    )
    quantity_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='عدد الكيلوات',
    )
    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر الكيلو',
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name='نوع الدفع')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='إجمالي البيع')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='إجمالي التكلفة')
    profit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='الربح')
    worker_cash_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='النقد المستلم على العامل',
    )
    cash_worker_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        limit_choices_to={'account_type': 'worker', 'is_active': True},
        related_name='cash_sales',
        verbose_name='حساب العامل النقدي',
    )
    payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        limit_choices_to={'account_type__in': ['cashbox', 'bank', 'wallet'], 'is_active': True},
        related_name='sales_payments',
        verbose_name='حساب الدفع',
    )
    is_new_accounting_sale = models.BooleanField(default=False, verbose_name='بيع محاسبي جديد')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    sale_date = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ البيع')

    class Meta:
        verbose_name = 'سطر بيع'
        verbose_name_plural = 'المبيعات'
        ordering = ['-sale_date']

    def __str__(self):
        return f"{self.product.name} - {self.worker.full_name} - {self.get_payment_type_display()}"

    def get_total_kg(self):
        return (Decimal(self.quantity_dabba) * DABBA_KG) + Decimal(self.quantity_kg)

    def clean(self):
        if self.quantity_dabba == 0 and self.quantity_kg == 0:
            raise ValidationError('يجب إدخال كمية مباعة.')

        if self.quantity_dabba > 0 and self.price_per_dabba <= 0:
            raise ValidationError('يجب إدخال سعر الدبة عند البيع بالدبة.')

        if self.quantity_kg > 0 and self.price_per_kg <= 0:
            raise ValidationError('يجب إدخال سعر الكيلو عند البيع بالكيلو.')

        if self.worker_id and not self.worker.warehouse and not (
            self.is_new_accounting_sale and self.worker.role == WorkerProfile.ROLE_MANAGER
        ):
            raise ValidationError('العامل غير مربوط بمخزن.')

        if self.worker_id and self.product_id and self.worker.warehouse and self.worker.warehouse != self.product.warehouse:
            raise ValidationError('هذا المنتج لا يتبع مخزن العامل.')

        uses_batch_accounting = self.batch_id and self.batch.uses_batch_accounting
        if self.is_new_accounting_sale and not uses_batch_accounting:
            if self.payment_type == 'cash':
                if not self.cash_worker_account_id:
                    raise ValidationError('يجب اختيار حساب العامل في البيع النقدي.')
                if self.cash_worker_account.account_type != 'worker':
                    raise ValidationError('حساب البيع النقدي يجب أن يكون من نوع عامل.')

            if self.payment_type == 'transfer':
                if not self.payment_account_id:
                    raise ValidationError('يجب اختيار الحساب المالي في بيع الحوالة.')
                if self.payment_account.account_type not in {'cashbox', 'bank', 'wallet'}:
                    raise ValidationError('حساب الحوالة يجب أن يكون صندوقًا أو بنكًا أو محفظة.')

            if self.payment_type == 'deferred' and not self.customer_id:
                raise ValidationError('في البيع الآجل يجب اختيار العميل.')

    def _restore_old_inventory(self):
        if not self.pk:
            return

        old_sale = Sale.objects.get(pk=self.pk)
        old_inventory = Inventory.objects.get(product=old_sale.product)
        restored_total = old_inventory.total_kg() + old_sale.get_total_kg()
        old_inventory.set_from_total_kg(restored_total)
        old_inventory.save()

    def _deduct_new_inventory(self):
        inventory = Inventory.objects.get(product=self.product)
        remaining_total = inventory.total_kg() - self.get_total_kg()

        if remaining_total < 0:
            raise ValidationError('الكمية المباعة أكبر من المخزون المتاح.')

        inventory.set_from_total_kg(remaining_total)
        inventory.save()

    def sync_worker_cash_transaction(self):
        from finance.models import WorkerAccountTransaction

        if self.batch_id and self.batch.uses_batch_accounting:
            WorkerAccountTransaction.objects.filter(sale=self).delete()
            return

        if self.payment_type == 'cash' and self.worker_cash_amount > 0:
            WorkerAccountTransaction.objects.update_or_create(
                sale=self,
                defaults={
                    'worker': self.worker,
                    'transaction_type': 'sale_cash',
                    'amount': self.worker_cash_amount,
                    'notes': f'بيع نقدي - {self.product.name}',
                },
            )
        else:
            WorkerAccountTransaction.objects.filter(sale=self).delete()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.worker and self.worker.warehouse:
            self.warehouse = self.worker.warehouse
        elif self.product_id:
            self.warehouse = self.product.warehouse
        if self.batch_id:
            self.store = self.batch.store

        dabba_sales_total = Decimal(self.quantity_dabba) * Decimal(self.price_per_dabba)
        kg_sales_total = Decimal(self.quantity_kg) * Decimal(self.price_per_kg)
        self.total_amount = money(dabba_sales_total + kg_sales_total)

        total_kg = self.get_total_kg()
        self.total_cost = money(total_kg * Decimal(self.product.purchase_price_per_kg))
        self.profit_amount = money(self.total_amount - self.total_cost)
        self.worker_cash_amount = money(self.total_amount) if self.payment_type == 'cash' else money(Decimal('0'))

        self.full_clean()

        if self.pk:
            self._restore_old_inventory()

        self._deduct_new_inventory()

        super().save(*args, **kwargs)
        self.sync_worker_cash_transaction()
        if self.is_new_accounting_sale:
            from .services import sync_sale_ledger

            sync_sale_ledger(self)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.is_new_accounting_sale and self.pk:
            from accounting.services import reverse_entries

            reverse_entries('sale', self.pk)

        inventory = Inventory.objects.get(product=self.product)
        restored_total = inventory.total_kg() + self.get_total_kg()
        inventory.set_from_total_kg(restored_total)
        inventory.save()

        super().delete(*args, **kwargs)

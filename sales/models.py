from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import WorkerProfile
from customers.models import Customer
from inventory.models import Inventory
from products.models import Product
from warehouses.models import Warehouse


DABBA_KG = Decimal('6.5')
MONEY_STEP = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقد'),
        ('transfer', 'حوالة'),
        ('deferred', 'آجل'),
    ]

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        verbose_name='المخزن'
    )

    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        verbose_name='العامل'
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='العميل'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='المنتج'
    )

    quantity_dabba = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد الدبب'
    )

    price_per_dabba = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر الدبة'
    )

    quantity_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name='عدد الكيلوات'
    )

    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر الكيلو'
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        verbose_name='نوع الدفع'
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي البيع'
    )

    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي التكلفة'
    )

    profit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='الربح'
    )

    worker_cash_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='النقد المستلم على العامل'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات'
    )

    sale_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ البيع'
    )

    class Meta:
        verbose_name = 'عملية بيع'
        verbose_name_plural = 'المبيعات'
        ordering = ['-sale_date']

    def __str__(self):
        return f"{self.product.name} - {self.worker.full_name} - {self.get_payment_type_display()}"

    def get_total_kg(self):
        return (Decimal(self.quantity_dabba) * DABBA_KG) + Decimal(self.quantity_kg)

    def clean(self):
        if self.payment_type == 'deferred' and not self.customer_id:
            raise ValidationError('في البيع الآجل يجب اختيار العميل.')

        if self.quantity_dabba == 0 and self.quantity_kg == 0:
            raise ValidationError('يجب إدخال كمية مباعة.')

        if self.quantity_dabba > 0 and self.price_per_dabba <= 0:
            raise ValidationError('يجب إدخال سعر الدبة عند البيع بالدبة.')

        if self.quantity_kg > 0 and self.price_per_kg <= 0:
            raise ValidationError('يجب إدخال سعر الكيلو عند البيع بالكيلو.')

        if self.worker_id:
            if not self.worker.warehouse:
                raise ValidationError('العامل غير مربوط بمخزن.')

        if self.worker_id and self.product_id:
            if self.worker.warehouse != self.product.warehouse:
                raise ValidationError('هذا المنتج لا يتبع مخزن العامل.')

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

        if self.payment_type == 'cash' and self.worker_cash_amount > 0:
            WorkerAccountTransaction.objects.update_or_create(
                sale=self,
                defaults={
                    'worker': self.worker,
                    'transaction_type': 'sale_cash',
                    'amount': self.worker_cash_amount,
                    'notes': f'بيع نقدي - {self.product.name}',
                }
            )
        else:
            WorkerAccountTransaction.objects.filter(sale=self).delete()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.worker and self.worker.warehouse:
            self.warehouse = self.worker.warehouse

        dabba_sales_total = Decimal(self.quantity_dabba) * Decimal(self.price_per_dabba)
        kg_sales_total = Decimal(self.quantity_kg) * Decimal(self.price_per_kg)

        self.total_amount = money(dabba_sales_total + kg_sales_total)

        total_kg = self.get_total_kg()
        self.total_cost = money(total_kg * Decimal(self.product.purchase_price_per_kg))
        self.profit_amount = money(self.total_amount - self.total_cost)

        if self.payment_type == 'cash':
            self.worker_cash_amount = money(self.total_amount)
        else:
            self.worker_cash_amount = money(Decimal('0'))

        self.full_clean()

        if self.pk:
            self._restore_old_inventory()

        self._deduct_new_inventory()

        super().save(*args, **kwargs)
        self.sync_worker_cash_transaction()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        inventory = Inventory.objects.get(product=self.product)
        restored_total = inventory.total_kg() + self.get_total_kg()
        inventory.set_from_total_kg(restored_total)
        inventory.save()

        super().delete(*args, **kwargs)
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from accounting.models import FinancialAccount
from inventory.models import DABBA_KG, Inventory
from products.models import Product

MONEY_STEP = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(MONEY_STEP)


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name='اسم المورد')
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='رقم الجوال')
    address = models.CharField(max_length=250, blank=True, null=True, verbose_name='العنوان')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مورد'
        verbose_name_plural = 'الموردون'
        ordering = ['name']

    def __str__(self):
        return self.name


class SupplierPurchase(models.Model):
    PAYMENT_PAID = 'paid'
    PAYMENT_UNPAID = 'unpaid'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PAID, 'مسدد'),
        (PAYMENT_UNPAID, 'آجل'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='supplier_purchases')

    quantity_dabba = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='عدد الدبب')
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='عدد الكيلوات')

    price_per_dabba = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='سعر الدبة')
    price_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='سعر الكيلو')

    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='إجمالي الشراء')
    add_to_inventory = models.BooleanField(default=False, verbose_name='إضافة الكمية للمخزون')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_UNPAID,
        verbose_name='حالة السداد',
    )
    payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='supplier_purchase_payments',
        verbose_name='حساب السداد',
    )
    is_new_accounting_purchase = models.BooleanField(default=False, verbose_name='شراء محاسبي جديد')
    purchase_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ الشراء')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'عملية شراء من مورد'
        verbose_name_plural = 'مشتريات الموردين'
        ordering = ['-purchase_date', '-created_at']

    def total_kg(self):
        return (Decimal(self.quantity_dabba) * DABBA_KG) + Decimal(self.quantity_kg)

    def clean(self):
        if self.quantity_dabba == 0 and self.quantity_kg == 0:
            raise ValidationError('يجب إدخال كمية الشراء.')
        if self.quantity_dabba > 0 and self.price_per_dabba <= 0:
            raise ValidationError('يجب إدخال سعر الدبة.')
        if self.quantity_kg > 0 and self.price_per_kg <= 0:
            raise ValidationError('يجب إدخال سعر الكيلو.')
        if self.is_new_accounting_purchase and self.payment_status == self.PAYMENT_PAID and not self.payment_account_id:
            raise ValidationError('في الشراء المسدد يجب اختيار الحساب المالي.')

    def _apply_inventory_delta(self, delta_kg):
        if delta_kg == 0:
            return

        inventory, _ = Inventory.objects.get_or_create(product=self.product)
        new_total = inventory.total_kg() + Decimal(delta_kg)

        if new_total < 0:
            raise ValidationError('لا يمكن تعديل الشراء لأن الكمية المطلوب خصمها أكبر من المخزون الحالي.')

        inventory.set_from_total_kg(new_total)
        inventory.save()

    @transaction.atomic
    def save(self, *args, **kwargs):
        old_purchase = None
        if self.pk:
            old_purchase = SupplierPurchase.objects.filter(pk=self.pk).select_related('product').first()

        dabba_total = self.quantity_dabba * self.price_per_dabba
        kg_total = self.quantity_kg * self.price_per_kg
        self.total_amount = money(dabba_total + kg_total)
        self.full_clean()

        super().save(*args, **kwargs)

        old_inventory_kg = old_purchase.total_kg() if old_purchase and old_purchase.add_to_inventory else Decimal('0')
        new_inventory_kg = self.total_kg() if self.add_to_inventory else Decimal('0')

        if old_purchase and old_purchase.product_id != self.product_id and old_inventory_kg:
            old_inventory = Inventory.objects.get(product=old_purchase.product)
            old_total = old_inventory.total_kg() - old_inventory_kg
            if old_total < 0:
                raise ValidationError('لا يمكن تعديل الشراء لأن الكمية القديمة أكبر من المخزون الحالي.')
            old_inventory.set_from_total_kg(old_total)
            old_inventory.save()
            self._apply_inventory_delta(new_inventory_kg)
        else:
            self._apply_inventory_delta(new_inventory_kg - old_inventory_kg)

        if self.is_new_accounting_purchase:
            from .services import sync_supplier_purchase_ledger

            sync_supplier_purchase_ledger(self)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.is_new_accounting_purchase and self.pk:
            from accounting.services import reverse_entries

            reverse_entries('supplier_purchase', self.pk)
        if self.add_to_inventory:
            self._apply_inventory_delta(-self.total_kg())
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.supplier.name} - {self.product.name} - {self.total_amount}'


class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='المبلغ المسدد')
    payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='supplier_payments',
        verbose_name='حساب السداد',
    )
    is_new_accounting_payment = models.BooleanField(default=False, verbose_name='سداد محاسبي جديد')
    payment_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ السداد')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سداد لمورد'
        verbose_name_plural = 'سداد الموردين'
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'{self.supplier.name} - {self.amount}'

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('مبلغ السداد يجب أن يكون أكبر من صفر.')
        if self.is_new_accounting_payment and not self.payment_account_id:
            raise ValidationError('يجب اختيار الحساب المالي لسداد المورد.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.is_new_accounting_payment:
            from .services import sync_supplier_payment_ledger

            sync_supplier_payment_ledger(self)

    def delete(self, *args, **kwargs):
        if self.is_new_accounting_payment and self.pk:
            from accounting.services import reverse_entries

            reverse_entries('supplier_payment', self.pk)
        super().delete(*args, **kwargs)

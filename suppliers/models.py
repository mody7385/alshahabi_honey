from django.db import models
from django.utils import timezone

from products.models import Product


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
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='supplier_purchases')

    quantity_dabba = models.PositiveIntegerField(default=0, verbose_name='عدد الدبب')
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='عدد الكيلوات')

    price_per_dabba = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='سعر الدبة')
    price_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='سعر الكيلو')

    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='إجمالي الشراء')
    purchase_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ الشراء')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'عملية شراء من مورد'
        verbose_name_plural = 'مشتريات الموردين'
        ordering = ['-purchase_date', '-created_at']

    def save(self, *args, **kwargs):
        dabba_total = self.quantity_dabba * self.price_per_dabba
        kg_total = self.quantity_kg * self.price_per_kg
        self.total_amount = dabba_total + kg_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.supplier.name} - {self.product.name} - {self.total_amount}'


class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='المبلغ المسدد')
    payment_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ السداد')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سداد لمورد'
        verbose_name_plural = 'سداد الموردين'
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'{self.supplier.name} - {self.amount}'
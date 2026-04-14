from django.db import models
from warehouses.models import Warehouse


class Product(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        verbose_name='المخزن'
    )
    name = models.CharField(max_length=150, verbose_name='اسم المنتج')
    honey_type = models.CharField(max_length=150, blank=True, null=True, verbose_name='نوع العسل')

    purchase_price_per_kg = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0,
    verbose_name='سعر الشراء للكيلو'
)

    default_sale_price_per_dabba = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر البيع الافتراضي للدبة'
    )

    default_sale_price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='سعر البيع الافتراضي للكيلو'
    )

    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'

    def __str__(self):
        return f"{self.name} - {self.warehouse.name}"
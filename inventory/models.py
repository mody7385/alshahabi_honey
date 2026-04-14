from decimal import Decimal

from django.db import models
from products.models import Product


DABBA_KG = Decimal('6.5')


class Inventory(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='المنتج'
    )
    full_dabba_count = models.PositiveIntegerField(default=0, verbose_name='عدد الدبب الكاملة')
    open_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='الكيلو المفتوح')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        verbose_name = 'مخزون'
        verbose_name_plural = 'المخزون'

    def __str__(self):
        return f"{self.product.name} - {self.product.warehouse.name}"

    def total_kg(self):
        return (Decimal(self.full_dabba_count) * DABBA_KG) + Decimal(self.open_kg)

    def set_from_total_kg(self, total_kg):
        total_kg = Decimal(total_kg)

        if total_kg < 0:
            raise ValueError('لا يمكن أن يكون المخزون بالسالب.')

        full_dabba = int(total_kg // DABBA_KG)
        remaining_kg = total_kg - (Decimal(full_dabba) * DABBA_KG)

        self.full_dabba_count = full_dabba
        self.open_kg = remaining_kg.quantize(Decimal('0.01'))
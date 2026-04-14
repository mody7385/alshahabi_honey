from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'warehouse',
        'honey_type',
        'purchase_price_per_kg',
        'default_sale_price_per_dabba',
        'default_sale_price_per_kg',
        'is_active',
    ]
    search_fields = ['name', 'honey_type', 'warehouse__name']
    list_filter = ['warehouse', 'is_active']
from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'warehouse',
        'worker',
        'customer',
        'payment_type',
        'quantity_dabba',
        'price_per_dabba',
        'quantity_kg',
        'price_per_kg',
        'total_amount',
        'sale_date',
    ]

    search_fields = [
        'product__name',
        'worker__full_name',
        'customer__name',
        'warehouse__name',
    ]

    list_filter = [
        'payment_type',
        'warehouse',
        'worker',
        'sale_date',
    ]

    readonly_fields = [
        'warehouse',
        'total_amount',
        'total_cost',
        'profit_amount',
        'worker_cash_amount',
        'sale_date',
    ]
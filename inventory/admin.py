from django.contrib import admin
from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'full_dabba_count', 'open_kg', 'updated_at']
    search_fields = ['product__name', 'product__warehouse__name']
    list_filter = ['product__warehouse']
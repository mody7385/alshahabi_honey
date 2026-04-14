from django.contrib import admin

from .models import WorkerProfile


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'user',
        'role',
        'warehouse',
        'phone',
        'is_active',
        'show_total_cash_sales',
        'show_total_expenses',
        'show_total_additions',
        'show_total_deductions',
        'show_final_balance',
        'show_balance_status',
    ]
    search_fields = [
        'full_name',
        'user__username',
        'phone',
    ]
    list_filter = [
        'role',
        'warehouse',
        'is_active',
    ]

    @admin.display(description='إجمالي البيع النقدي')
    def show_total_cash_sales(self, obj):
        return obj.total_cash_sales()

    @admin.display(description='إجمالي المصروفات')
    def show_total_expenses(self, obj):
        return obj.total_expenses()

    @admin.display(description='إجمالي الإضافات')
    def show_total_additions(self, obj):
        return obj.total_additions()

    @admin.display(description='إجمالي الخصومات')
    def show_total_deductions(self, obj):
        return obj.total_deductions()

    @admin.display(description='الرصيد النهائي')
    def show_final_balance(self, obj):
        return obj.final_balance()

    @admin.display(description='الحالة')
    def show_balance_status(self, obj):
        return obj.balance_status()
from django.contrib import admin
from .models import WorkerAccountTransaction


@admin.register(WorkerAccountTransaction)
class WorkerAccountTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'worker',
        'transaction_type',
        'amount',
        'sale',
        'created_at',
    ]

    search_fields = [
        'worker__full_name',
        'worker__user__username',
        'notes',
    ]

    list_filter = [
        'transaction_type',
        'worker',
        'created_at',
    ]

    readonly_fields = ['created_at']

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)

        if obj and obj.transaction_type == 'sale_cash':
            readonly.extend(['worker', 'sale', 'transaction_type', 'amount', 'notes'])

        return readonly
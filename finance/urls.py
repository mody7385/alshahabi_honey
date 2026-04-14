from django.urls import path

from .views import (
    manager_add_worker_transaction,
    manager_operating_expense_create,
    manager_operating_expense_delete,
    manager_operating_expense_update,
    manager_profit_center,
)

urlpatterns = [
    path('manager/worker/<int:worker_pk>/add-transaction/', manager_add_worker_transaction, name='manager-add-worker-transaction'),
    path('manager/profit-center/', manager_profit_center, name='manager-profit-center'),
    path('manager/profit-center/expenses/add/', manager_operating_expense_create, name='manager-operating-expense-create'),
    path('manager/profit-center/expenses/<int:pk>/edit/', manager_operating_expense_update, name='manager-operating-expense-update'),
    path('manager/profit-center/expenses/<int:pk>/delete/', manager_operating_expense_delete, name='manager-operating-expense-delete'),
]
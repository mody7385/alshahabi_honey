from django.urls import path

from . import views


urlpatterns = [
    path('accounts/', views.account_list, name='accounting-account-list'),
    path('accounts/add/', views.account_create, name='accounting-account-create'),
    path('accounts/<int:pk>/', views.account_detail, name='accounting-account-detail'),
    path('accounts/<int:pk>/edit/', views.account_update, name='accounting-account-update'),
    path('adjustments/add/', views.manual_adjustment, name='accounting-manual-adjustment'),
    path('adjustments/<int:pk>/void/', views.manual_adjustment_void, name='accounting-manual-adjustment-void'),
    path('transfers/add/', views.transfer_create, name='accounting-transfer-create'),
    path('transfers/<int:pk>/edit/', views.transfer_update, name='accounting-transfer-update'),
    path('transfers/<int:pk>/delete/', views.transfer_delete, name='accounting-transfer-delete'),
    path('deferred-customers/', views.deferred_customer_list, name='accounting-deferred-customer-list'),
    path('deferred-customers/<int:pk>/', views.customer_statement, name='accounting-customer-statement'),
    path('customer-payments/add/', views.customer_payment_create, name='accounting-customer-payment-create'),
    path('customer-payments/customer/<int:customer_pk>/add/', views.customer_payment_create, name='accounting-customer-payment-create-for-customer'),
    path('customer-payments/<int:pk>/edit/', views.customer_payment_update, name='accounting-customer-payment-update'),
    path('customer-payments/<int:pk>/delete/', views.customer_payment_delete, name='accounting-customer-payment-delete'),
    path('reports/', views.reports_dashboard, name='accounting-reports-dashboard'),
    path('reports/accounts/', views.account_balances_report, name='accounting-account-balances-report'),
    path('reports/profit/', views.profit_report, name='accounting-profit-report'),
    path('reports/cashflow/', views.cashflow_report, name='accounting-cashflow-report'),
    path('reports/workers/', views.worker_balances_report, name='accounting-worker-balances-report'),
    path('reports/personal-expenses/', views.personal_expenses_report, name='accounting-personal-expenses-report'),
]

from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    dashboard,
    manager_customers_list,
    manager_dashboard,
    manager_inventory_list,
    manager_inventory_adjust,
    manager_products_list,
    manager_reports,
    manager_sales_list,
    manager_warehouses_list,
    manager_worker_account_detail,
    manager_worker_accounts_list,
    manager_product_create,
    manager_product_update,
    worker_account_summary,
    manager_warehouse_create,
    manager_warehouse_update,
    manager_user_create,
    manager_user_update,
    manager_users_list,
    
)

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('manager-dashboard/', manager_dashboard, name='manager-dashboard'),
    path('manager-warehouses/', manager_warehouses_list, name='manager-warehouses-list'),
    path('manager-warehouses/add/', manager_warehouse_create, name='manager-warehouse-create'),
    path('manager-warehouses/<int:pk>/edit/', manager_warehouse_update, name='manager-warehouse-update'),
    path('manager-products/', manager_products_list, name='manager-products-list'),
    path('manager-products/add/', manager_product_create, name='manager-product-create'),
    path('manager-products/<int:pk>/edit/', manager_product_update, name='manager-product-update'),
    path('manager-inventory/', manager_inventory_list, name='manager-inventory-list'),
    path('manager-inventory/<int:pk>/adjust/', manager_inventory_adjust, name='manager-inventory-adjust'),
    path('manager-customers/', manager_customers_list, name='manager-customers-list'),
    path('manager-sales/', manager_sales_list, name='manager-sales-list'),
    path('manager-worker-accounts/', manager_worker_accounts_list, name='manager-worker-accounts-list'),
    path('manager-worker-accounts/<int:pk>/', manager_worker_account_detail, name='manager-worker-account-detail'),
    path('manager-reports/', manager_reports, name='manager-reports'),
    path('my-account/', worker_account_summary, name='worker-account-summary'),
    path('manager-users/', manager_users_list, name='manager-users-list'),
    path('manager-users/add/', manager_user_create, name='manager-user-create'),
    path('manager-users/<int:pk>/edit/', manager_user_update, name='manager-user-update'),
]
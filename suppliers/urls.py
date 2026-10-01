from django.urls import path

from .views import (
    supplier_create,
    supplier_detail,
    supplier_list,
    supplier_payment_create,
    supplier_payment_delete,
    supplier_payment_update,
    supplier_purchase_create,
    supplier_purchase_delete,
    supplier_purchase_update,
    supplier_update,
)

urlpatterns = [
    path('', supplier_list, name='supplier-list'),
    path('add/', supplier_create, name='supplier-create'),
    path('<int:pk>/', supplier_detail, name='supplier-detail'),
    path('<int:pk>/edit/', supplier_update, name='supplier-update'),
    path('purchase/add/', supplier_purchase_create, name='supplier-purchase-create'),
    path('purchase/<int:pk>/edit/', supplier_purchase_update, name='supplier-purchase-update'),
    path('purchase/<int:pk>/delete/', supplier_purchase_delete, name='supplier-purchase-delete'),
    path('payment/add/', supplier_payment_create, name='supplier-payment-create'),
    path('payment/<int:pk>/edit/', supplier_payment_update, name='supplier-payment-update'),
    path('payment/<int:pk>/delete/', supplier_payment_delete, name='supplier-payment-delete'),
]

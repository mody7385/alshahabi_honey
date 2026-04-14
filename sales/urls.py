from django.urls import path

from .views import (
    sale_delete,
    sale_update,
    worker_sale_create,
    worker_sale_detail,
    worker_sales_list,
)

urlpatterns = [
    path('worker/create/', worker_sale_create, name='worker-sale-create'),
    path('worker/list/', worker_sales_list, name='worker-sales-list'),
    path('<int:pk>/', worker_sale_detail, name='worker-sale-detail'),
    path('<int:pk>/edit/', sale_update, name='sale-update'),
    path('<int:pk>/delete/', sale_delete, name='sale-delete'),
]
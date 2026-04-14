from django.urls import path

from .views import worker_inventory_list

urlpatterns = [
    path('worker/list/', worker_inventory_list, name='worker-inventory-list'),
]